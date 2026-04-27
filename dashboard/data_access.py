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
    prefix = "bronze/gym_counts/"
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
    """
    Return sorted list of all days that have S3 data.

    Uses delimiter listing against a single sample location — O(years × months)
    paginator calls instead of listing all 17 k objects.
    """
    locations = get_available_locations()
    if not locations:
        return []

    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    # SWRC Fitness Total is the only partition with the full historical
    # archive (back to 2025); newer per-room partitions only start when
    # ingestion was rebuilt. Fall back to alphabetical if absent.
    sample_loc = "SWRC Fitness Total" if "SWRC Fitness Total" in locations else locations[0]
    base = f"bronze/gym_counts/location_name={sample_loc}/"
    dates: list[date] = []

    try:
        # Level 1 — year= folders
        for ypage in paginator.paginate(Bucket=BUCKET, Prefix=base, Delimiter="/"):
            for ycp in ypage.get("CommonPrefixes", []):
                try:
                    year = int(ycp["Prefix"].split("year=")[-1].rstrip("/"))
                except (ValueError, IndexError):
                    continue

                # Level 2 — month= folders
                for mpage in paginator.paginate(Bucket=BUCKET, Prefix=ycp["Prefix"], Delimiter="/"):
                    for mcp in mpage.get("CommonPrefixes", []):
                        try:
                            month = int(mcp["Prefix"].split("month=")[-1].rstrip("/"))
                        except (ValueError, IndexError):
                            continue

                        # Level 3 — day= folders
                        for dpage in paginator.paginate(Bucket=BUCKET, Prefix=mcp["Prefix"], Delimiter="/"):
                            for dcp in dpage.get("CommonPrefixes", []):
                                try:
                                    day = int(dcp["Prefix"].split("day=")[-1].rstrip("/"))
                                    dates.append(date(year, month, day))
                                except (ValueError, IndexError):
                                    continue
    except Exception as exc:
        log.error("Error fetching available dates: %s", exc)

    return sorted(dates)


# ── Data loading ──────────────────────────────────────────────────────────────

def _build_prefixes(locations: list[str], start: date, end: date) -> list[str]:
    """Build all S3 prefixes for a location × date range cross product."""
    prefixes = []
    current = start
    while current <= end:
        for loc in locations:
            prefixes.append(
                f"bronze/gym_counts/location_name={loc}/"
                f"year={current.year}/month={current.month:02d}/day={current.day:02d}/"
            )
        current += timedelta(days=1)
    return prefixes


def _list_csv_keys(s3, prefix: str) -> list[str]:
    """Return all .csv object keys under a prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    try:
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".csv"):
                    keys.append(obj["Key"])
    except Exception as exc:
        log.warning("Could not list %s: %s", prefix, exc)
    return keys


@st.cache_data(ttl=600)
def load_data_from_s3(
    start_date: date,
    end_date: date,
    locations: list[str],
) -> pd.DataFrame:
    """
    Load all hourly CSV files from S3 for the given date range and locations.
    Results are cached for 10 minutes. Returns an empty DataFrame on failure.
    """
    s3 = get_s3_client()
    prefixes = _build_prefixes(locations, start_date, end_date)

    frames: list[pd.DataFrame] = []
    failed = 0

    for prefix in prefixes:
        for key in _list_csv_keys(s3, prefix):
            try:
                obj = s3.get_object(Bucket=BUCKET, Key=key)
                frames.append(pd.read_csv(io.BytesIO(obj["Body"].read())))
            except Exception as exc:
                log.warning("Failed to read %s: %s", key, exc)
                failed += 1

    if not frames:
        return pd.DataFrame()

    if failed:
        log.warning("%d files could not be read", failed)

    return pd.concat(frames, ignore_index=True)
