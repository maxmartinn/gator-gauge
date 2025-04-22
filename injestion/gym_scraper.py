import requests
import csv
import os
from datetime import datetime, timezone
from time import sleep

URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount?AccountAPIKey=8e2c21d2-6f5d-45c1-af9e-c23aebfda68b"
CSV_FILE = "/Users/maxmartin/projects/gator-gauge/data/raw/gym_raw_data.csv"

def fetch_json():
    r = requests.get(URL)
    r.raise_for_status()
    return r.json()

def format_rows(json_data):
    now = datetime.now(timezone.utc).isoformat()
    rows = []

    for loc in json_data:
        try:
            count = int(loc["LastCount"])
            capacity = int(loc["TotalCapacity"])
            percent = round((count / capacity) * 100, 2) if capacity > 0 else 0
            rows.append({
                "pulled_at_utc": now,
                "facility_name": loc["FacilityName"].strip(),
                "location_name": loc["LocationName"].strip(),
                "last_count": count,
                "total_capacity": capacity,
                "percent_full": percent,
                "last_updated_source_time": loc["LastUpdatedDateAndTime"],
                "is_closed": loc["IsClosed"],
            })
        except Exception as e:
            print(f"❌ Skipping location due to error: {e}")
    return rows

def write_csv(rows):
    os.makedirs(os.path.dirname(CSV_FILE) or ".", exist_ok=True)
    write_header = not os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    data = fetch_json()
    rows = format_rows(data)
    while True:
        if rows:
            write_csv(rows)
            print(f"✅ Logged {len(rows)} entries to {CSV_FILE}")
        else:
            print("⚠️ No data to write.")
        sleep(60)
