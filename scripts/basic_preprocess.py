import pandas as pd
from pathlib import Path
from datetime import timezone
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def load_data(path: Path) -> pd.DataFrame:
    logging.info(f"📥 Loading raw data from {path}")
    try:
        return pd.read_csv(path)
    except Exception as e:
        logging.error(f"❌ Failed to load data: {e}")
        sys.exit(1)

def make_timestamps_utc(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("🕒 Normalizing timestamps to UTC")
    for col in ['pulled_at_utc', 'last_updated_source_time']:
        df[col] = pd.to_datetime(df[col], utc=True, errors='coerce')
    return df

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("🛠 Engineering time-based features")
    df['hour'] = df['pulled_at_utc'].dt.hour
    df['day_of_week'] = df['pulled_at_utc'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6])
    return df

def transform(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("🔄 Transforming data and one-hot encoding")
    return pd.get_dummies(df[[
        'location_name', 'hour', 'day_of_week', 'is_weekend',
        'last_count', 'total_capacity', 'percent_full', 'is_closed'
    ]], columns=['location_name'])

def save_data(df: pd.DataFrame, path: Path):
    logging.info(f"💾 Saving processed data to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def main():
    raw_path = Path("../data/raw/gym_raw_data.csv")
    processed_path = Path("../data/processed/gym_processed_data.csv")

    df = load_data(raw_path)
    df = make_timestamps_utc(df)
    df = engineer_features(df)
    df = transform(df)
    save_data(df, processed_path)

    logging.info("✅ Preprocessing complete")

if __name__ == "__main__":
    main()
