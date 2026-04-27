import io
import logging
from datetime import date, timedelta
from typing import Optional

import boto3
import pandas as pd
import streamlit as st

BUCKET = "gator-gains-data"
REGION = "us-east-1"

log = logging.getLogger(__name__)


def get_s3_client():
    """Create and return an S3 client using the ambient AWS profile."""
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
    """Return sorted list of days the silver layer has data for."""
    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    months: set[tuple[int, int]] = set()
    sample = "SWRC Fitness Total"
    base = f"silver/gym_counts/location_name={sample}/"
    try:
        for page in paginator.paginate(Bucket=BUCKET, Prefix=base):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                try:
                    y = int(key.split("/year=")[1].split("/")[0])
                    m = int(key.split("/month=")[1].split("/")[0])
                    months.add((y, m))
                except (IndexError, ValueError):
                    continue
    except Exception as exc:
        log.error("Error fetching available dates: %s", exc)

    dates: list[date] = []
    for year, month in sorted(months):
        d = date(year, month, 1)
        # Day 1 of each month is enough — Streamlit treats the picker as a range.
        dates.append(d)
        # Last day available — approximate via month end (works for the picker).
        next_month = date(year + (month // 12), (month % 12) + 1, 1)
        dates.append(next_month - timedelta(days=1))
    return sorted(set(dates))


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
                frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["pulled_at_utc"] = pd.to_datetime(df["pulled_at_utc"], utc=True, format="mixed")
    end_inclusive = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    return df[(df["pulled_at_utc"] >= pd.Timestamp(start_date, tz="UTC"))
              & (df["pulled_at_utc"] < end_inclusive)].reset_index(drop=True)
