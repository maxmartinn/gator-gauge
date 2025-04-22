import pandas as pd
import joblib
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import time



# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Paths
DATA_PATH = Path("data/processed/gym_processed_data.csv")
MODEL_PATH = Path("models/gym_model.pkl")

def load_data(path: Path) -> pd.DataFrame:
    logging.info(f"Loading processed data from {path}")
    return pd.read_csv(path)

def train_model(X_train, y_train) -> RandomForestRegressor:
    logging.info("Training RandomForestRegressor model...")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    logging.info("Evaluating model...")
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    mse = mean_squared_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    logging.info(f"Model Performance:")
    logging.info(f"  - MAE: {mae:.2f}")
    logging.info(f"  - MSE: {mse:.2f}")
    logging.info(f"  - R^2: {r2:.4f}")

def save_model(model, path: Path):
    logging.info(f"Saving model to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)

def main():
    start = time.time()
    df = load_data(DATA_PATH)

    # Split features and target
    X = df.drop(columns=["last_count", "percent_full"] )
    y = df["last_count"]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train and evaluate
    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)
    save_model(model, MODEL_PATH)

    
    print(f"Training completed in {time.time() - start:.2f} seconds")

    logging.info("Training complete.")

if __name__ == "__main__":
    main()
