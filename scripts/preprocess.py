import pandas as pd
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO)


logging.info("Starting Preproccessing")
# Paths

raw_path = Path("../data/raw/gym_raw_data.csv")
processed_path = Path("../data/processed/gym_processed_data.csv")

# Load
df = pd.read_csv(raw_path)

# Convert timestamps
df['pulled_at_utc'] = pd.to_datetime(df['pulled_at_utc'])
df['hour'] = df['pulled_at_utc'].dt.hour
df['day_of_week'] = df['pulled_at_utc'].dt.dayofweek
df['is_weekend'] = df['day_of_week'].isin([5, 6])

# Select & one-hot encode
df = pd.get_dummies(df[[
    'location_name', 'hour', 'day_of_week', 'is_weekend',
    'last_count', 'total_capacity', 'percent_full', 'is_closed'
]], columns=['location_name'])

# Save
processed_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(processed_path, index=False)
