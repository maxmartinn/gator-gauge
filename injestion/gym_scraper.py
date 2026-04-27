import argparse
import csv
import io
import logging
import os
from datetime import datetime, timezone

import boto3
import requests

logging.basicConfig(level=logging.INFO)

URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount?AccountAPIKey=8e2c21d2-6f5d-45c1-af9e-c23aebfda68b"
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
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    return r.json()


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
            last_updated_source_time = (
                datetime.fromisoformat(loc["LastUpdatedDateAndTime"])
                .astimezone(timezone.utc)
                .isoformat()
            )
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
    key = f"{prefix}/dt={now:%Y-%m-%d}/gym_counts_{now:%Y%m%dT%H%M%SZ}.csv"
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=rows_to_csv_bytes(rows),
        ContentType="text/csv",
    )
    logging.info(f"Uploaded {len(rows)} rows to s3://{bucket}/{key}")


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
