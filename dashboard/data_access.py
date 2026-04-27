import io
import logging
from datetime import date
from typing import Optional

import boto3
import pandas as pd
import streamlit as st

BUCKET = "gator-gains-data"
REGION = "us-east-1"

log = logging.getLogger(__name__)


def get_s3_client():
    """Create and return an S3 client using Streamlit secrets or ambient AWS config."""
    try:
        aws_secrets = st.secrets.get("aws", {})
    except FileNotFoundError:
        aws_secrets = {}
    if aws_secrets:
        return boto3.client(
            "s3",
            region_name=aws_secrets.get("region_name", REGION),
            aws_access_key_id=str(aws_secrets.get("aws_access_key_id", "")).strip(),
            aws_secret_access_key=str(aws_secrets.get("aws_secret_access_key", "")).strip(),
        )
    return boto3.client("s3", region_name=REGION)


# ── Catalog discovery ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_available_locations() -> list[str]:
    """
    Return sorted list of all location_name= folder values in S3.
    Uses delimiter listing — fast, O(1) paginator calls.
    """
    s3 = get_s3_client()
    prefix = "silver/gym_counts/"
    paginator = s3.get_paginator("list_objects_v2")
    locations = []

    try:
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix, Delimiter="/"):
            for cp in page.get("CommonPrefixes", []):
                folder = cp["Prefix"]
                if "location_name=" in folder:
                    loc = folder.split("location_name=")[-1].rstrip("/")
                    locations.append(loc)
    except Exception as exc:
        log.error("Error listing locations: %s", exc)

    return sorted(locations)


@st.cache_data(ttl=3600)
def get_available_dates() -> list[date]:
    """Return sorted list of actual days the silver layer has data for."""
    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    dates: set[date] = set()
    sample = "SWRC Fitness Total"
    base = f"silver/gym_counts/location_name={sample}/"
    try:
        for page in paginator.paginate(Bucket=BUCKET, Prefix=base):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("/data.parquet"):
                    continue
                body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
                df = pd.read_parquet(io.BytesIO(body), columns=["pulled_at_utc"])
                pulled_at = pd.to_datetime(df["pulled_at_utc"], utc=True, format="mixed")
                dates.update(pulled_at.dt.date.dropna().unique())
    except Exception as exc:
        log.error("Error fetching available dates: %s", exc)

    return sorted(dates)


# ── Data loading ──────────────────────────────────────────────────────────────

def _months_in_range(start: date, end: date) -> list[tuple[int, int]]:
    """Yield every (year, month) tuple between start and end inclusive."""
    months: list[tuple[int, int]] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m > 12:
            y += 1
            m = 1
    return months


def _read_silver_parquet(s3, key: str) -> Optional[pd.DataFrame]:
    try:
        body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        return pd.read_parquet(io.BytesIO(body))
    except Exception as exc:
        log.warning("Could not read %s: %s", key, exc)
        return None


@st.cache_data(ttl=600)
def _silver_manifest() -> set[str]:
    """Return the set of every silver Parquet key currently in the bucket."""
    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    keys: set[str] = set()
    for page in paginator.paginate(Bucket=BUCKET, Prefix="silver/gym_counts/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("/data.parquet"):
                keys.add(obj["Key"])
    return keys


@st.cache_data(ttl=600)
def load_data_from_s3(
    start_date: date,
    end_date: date,
    locations: list[str],
) -> pd.DataFrame:
    """Load silver Parquet files for the requested location × month grid."""
    s3 = get_s3_client()
    manifest = _silver_manifest()
    frames: list[pd.DataFrame] = []
    for loc in locations:
        for year, month in _months_in_range(start_date, end_date):
            key = (
                f"silver/gym_counts/location_name={loc}/"
                f"year={year}/month={month:02d}/data.parquet"
            )
            if key not in manifest:
                continue
            df = _read_silver_parquet(s3, key)
            if df is not None and not df.empty:
                # The S3 partition is the selected location contract. Some older
                # silver files carry legacy display names inside the parquet rows.
                df["location_name"] = loc
                frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["pulled_at_utc"] = pd.to_datetime(df["pulled_at_utc"], utc=True, format="mixed")
    end_inclusive = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    return df[(df["pulled_at_utc"] >= pd.Timestamp(start_date, tz="UTC"))
              & (df["pulled_at_utc"] < end_inclusive)].reset_index(drop=True)
