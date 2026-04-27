import argparse
import csv
import io
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import boto3
import requests

SOURCE_TIMEZONE = ZoneInfo("America/New_York")

logging.basicConfig(level=logging.INFO)

DEFAULT_API_BASE_URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount"
CSV_FILE = "data/raw/gym_raw_data.csv"
ALLOWED_LOCATIONS = {
    "SWRC Weight Room",
    "SWRC Cardio Room 1",
    "SWRC Cardio Room 2",
    "Multi-Purpose Court 1",
    "Multi-Purpose Court 2",
    "Multi-Purpose Court 3",
    "Multi-Purpose Court 4",
    "Multi-Purpose Court 5",
    "Multi-Purpose Court 6",
    "SWRC Tennis Courts",
    "SRFC Weight Room",
    "SRFC Cardio Room",
    "SRFC Lower Functional Area",
    "SRFC Squash",
    "SRFC Table Tennis",
    "SRFC Multi-purpose Court",
    "SRFC Racquetball",
    "Florida Pool",
}

AGGREGATES = {
    "SWRC Fitness Total": {
        "facility_name": "SWRC",
        "members": ["SWRC Weight Room", "SWRC Cardio Room 1", "SWRC Cardio Room 2"],
    },
    "SRFC Fitness Total": {
        "facility_name": "SRFC",
        "members": ["SRFC Weight Room", "SRFC Cardio Room", "SRFC Lower Functional Area"],
    },
}

FIELDNAMES = [
    "pulled_at_utc",
    "facility_name",
    "location_name",
    "last_count",
    "total_capacity",
    "percent_full",
    "last_updated_source_time",
    "is_closed",
]


def fetch_json():
    url = os.environ.get("GATOR_GAUGE_API_URL")
    api_key = os.environ.get("GATOR_GAUGE_ACCOUNT_API_KEY")
    if not url and api_key:
        url = f"{DEFAULT_API_BASE_URL}?AccountAPIKey={api_key}"
    if not url:
        raise RuntimeError(
            "Set GATOR_GAUGE_API_URL or GATOR_GAUGE_ACCOUNT_API_KEY before running ingestion."
        )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.SSLError:
        logging.warning("Python SSL request failed; retrying with curl")
        completed = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", url],
            capture_output=True, check=True, text=True, timeout=15,
        )
        return json.loads(completed.stdout)


def parse_source_time(value):
    text = str(value).strip().rstrip("Z")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SOURCE_TIMEZONE)
    return parsed.astimezone(timezone.utc).isoformat()


def format_rows(json_data):
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for loc in json_data:
        if loc.get("LocationName", "").strip() not in ALLOWED_LOCATIONS:
            continue
        try:
            count = int(loc["LastCount"])
            capacity = int(loc["TotalCapacity"])
            percent = round((count / capacity) * 100, 2) if capacity > 0 else 0
            last_updated_source_time = parse_source_time(loc["LastUpdatedDateAndTime"])
            rows.append({
                "pulled_at_utc": now,
                "facility_name": loc["FacilityName"].strip(),
                "location_name": loc["LocationName"].strip(),
                "last_count": count,
                "total_capacity": capacity,
                "percent_full": percent,
                "last_updated_source_time": last_updated_source_time,
                "is_closed": loc["IsClosed"],
            })
        except Exception as e:
            logging.error(f"Skipping location due to error: {e}")

    by_location = {r["location_name"]: r for r in rows}
    for agg_name, agg in AGGREGATES.items():
        members = [by_location[m] for m in agg["members"] if m in by_location]
        if not members:
            continue
        total_count = sum(m["last_count"] for m in members)
        total_capacity = sum(m["total_capacity"] for m in members)
        percent = round((total_count / total_capacity) * 100, 2) if total_capacity > 0 else 0
        latest_source = max(m["last_updated_source_time"] for m in members)
        rows.append({
            "pulled_at_utc": now,
            "facility_name": agg["facility_name"],
            "location_name": agg_name,
            "last_count": total_count,
            "total_capacity": total_capacity,
            "percent_full": percent,
            "last_updated_source_time": latest_source,
            "is_closed": all(m["is_closed"] for m in members),
        })
    return rows


def rows_to_csv_bytes(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def write_csv_local(rows):
    os.makedirs(os.path.dirname(CSV_FILE) or ".", exist_ok=True)
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def upload_to_s3(rows):
    bucket = os.environ["GATOR_GAUGE_S3_BUCKET"]
    prefix = os.environ.get("GATOR_GAUGE_S3_PREFIX", "bronze/gym_counts").strip("/")
    now = datetime.now(timezone.utc)
    s3 = boto3.client("s3")
    for row in rows:
        location = row["location_name"].replace("/", "_")
        key = (
            f"{prefix}/location_name={location}"
            f"/year={now:%Y}/month={now:%m}/day={now:%d}"
            f"/gym_data_{now:%Y%m%dT%H%M%SZ}.csv"
        )
        body = rows_to_csv_bytes([row])
        s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/csv")
    logging.info(f"Uploaded {len(rows)} per-location objects to s3://{bucket}/{prefix}/")


def silver_key(prefix, location, year, month):
    return (
        f"{prefix}/location_name={location.replace('/', '_')}"
        f"/year={year}/month={month:02d}/data.parquet"
    )


def upload_silver(rows):
    """Append the new rows into each location's current-month silver Parquet."""
    import pandas as pd

    bucket = os.environ["GATOR_GAUGE_S3_BUCKET"]
    prefix = os.environ.get("GATOR_GAUGE_SILVER_PREFIX", "silver/gym_counts").strip("/")
    now = datetime.now(timezone.utc)
    s3 = boto3.client("s3")

    by_loc = {}
    for r in rows:
        by_loc.setdefault(r["location_name"], []).append(r)

    for location, loc_rows in by_loc.items():
        key = silver_key(prefix, location, now.year, now.month)
        new_df = pd.DataFrame(loc_rows)
        try:
            existing = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            old_df = pd.read_parquet(io.BytesIO(existing))
            df = pd.concat([old_df, new_df], ignore_index=True)
        except Exception:
            df = new_df
        df = df.drop_duplicates(subset=["pulled_at_utc", "location_name"], keep="last")
        df = df.sort_values("pulled_at_utc")
        buf = io.BytesIO()
        df.to_parquet(buf, index=False, compression="snappy")
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue(), ContentType="application/octet-stream")
    logging.info(f"Updated {len(by_loc)} silver Parquet files for {now:%Y-%m}")


def run(no_local=False, no_s3=False):
    logging.info("Gym scraper started")
    rows = format_rows(fetch_json())
    if not rows:
        logging.warning("No data to write.")
        return 0
    if not no_local:
        write_csv_local(rows)
        logging.info(f"Logged {len(rows)} entries to {CSV_FILE}")
    if not no_s3:
        upload_to_s3(rows)
        try:
            upload_silver(rows)
        except Exception as e:
            logging.error(f"Silver rollup failed (bronze still uploaded): {e}")
    return len(rows)


def lambda_handler(event, context):
    count = run(no_local=True, no_s3=False)
    return {"rows": count}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--no-local", action="store_true")
    p.add_argument("--no-s3", action="store_true")
    args = p.parse_args()
    run(no_local=args.no_local, no_s3=args.no_s3)
