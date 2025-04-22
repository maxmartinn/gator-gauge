import pandas as pd
from pathlib import Path
from datetime import timezone

# Load CSV
raw_path = Path("../data/raw/gym_raw_data.csv")
output_path = Path("../data/processed/gym_raw_data_utc_normalized.csv")

df = pd.read_csv(raw_path)

# Convert to datetime, add UTC only if missing
def force_utc(ts):
    dt = pd.to_datetime(ts, utc=False)  # Parse first
    if dt.tzinfo is None:               # If no timezone
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Apply to both timestamp columns
df['pulled_at_utc'] = df['pulled_at_utc'].apply(force_utc)
df['last_updated_source_time'] = df['last_updated_source_time'].apply(force_utc)

# Save the updated CSV with +00:00 preserved
output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)

print(f"✅ Saved normalized UTC data to {output_path}")
