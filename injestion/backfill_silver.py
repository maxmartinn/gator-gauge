"""
Build silver-layer Parquet files from existing bronze CSVs.

For every (location_name, year, month) in bronze, reads all per-hour CSVs
under that prefix, concatenates them, dedups by (pulled_at_utc, location_name),
and writes a single Parquet to:

    s3://<bucket>/silver/gym_counts/location_name=<loc>/year=YYYY/month=MM/data.parquet

Idempotent: re-running rebuilds Parquet files in place.

Usage:
    python injestion/backfill_silver.py --bucket gator-gains-data
    python injestion/backfill_silver.py --location "SWRC Fitness Total"
    python injestion/backfill_silver.py --year 2026 --month 4
"""
import argparse
import io
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BRONZE_PREFIX = "bronze/gym_counts"
SILVER_PREFIX = "silver/gym_counts"


def list_locations(s3, bucket):
    p = s3.get_paginator("list_objects_v2")
    for page in p.paginate(Bucket=bucket, Prefix=f"{BRONZE_PREFIX}/", Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            folder = cp["Prefix"]
            if "location_name=" in folder:
                yield folder.split("location_name=")[-1].rstrip("/")


def list_keys_for_location(s3, bucket, location):
    p = s3.get_paginator("list_objects_v2")
    prefix = f"{BRONZE_PREFIX}/location_name={location}/"
    for page in p.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".csv"):
                yield obj["Key"]


def parse_year_month(key):
    """Extract (year, month) from a key like .../year=2026/month=04/day=27/...csv."""
    try:
        y = int(key.split("/year=")[1].split("/")[0])
        m = int(key.split("/month=")[1].split("/")[0])
        return y, m
    except (IndexError, ValueError):
        return None


def read_csv(s3, bucket, key):
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(body))


def build_month(s3, bucket, location, year, month, keys):
    if not keys:
        return 0
    with ThreadPoolExecutor(max_workers=32) as pool:
        futures = [pool.submit(read_csv, s3, bucket, k) for k in keys]
        frames = [f.result() for f in as_completed(futures)]
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["pulled_at_utc", "location_name"], keep="last")
    df = df.sort_values("pulled_at_utc")

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, compression="snappy")
    silver_key = (
        f"{SILVER_PREFIX}/location_name={location.replace('/', '_')}"
        f"/year={year}/month={month:02d}/data.parquet"
    )
    s3.put_object(Bucket=bucket, Key=silver_key, Body=buf.getvalue())
    logging.info("Wrote %d rows → s3://%s/%s", len(df), bucket, silver_key)
    return len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", default="gator-gains-data")
    ap.add_argument("--location", help="Only this location")
    ap.add_argument("--year", type=int, help="Only this year")
    ap.add_argument("--month", type=int, help="Only this month")
    args = ap.parse_args()

    s3 = boto3.client("s3")
    locations = [args.location] if args.location else sorted(list_locations(s3, args.bucket))

    for location in locations:
        keys_by_month = defaultdict(list)
        for key in list_keys_for_location(s3, args.bucket, location):
            ym = parse_year_month(key)
            if ym is None:
                continue
            if args.year and ym[0] != args.year:
                continue
            if args.month and ym[1] != args.month:
                continue
            keys_by_month[ym].append(key)

        logging.info("%s: %d months to build", location, len(keys_by_month))
        for (year, month), keys in sorted(keys_by_month.items()):
            build_month(s3, args.bucket, location, year, month, keys)


if __name__ == "__main__":
    main()
