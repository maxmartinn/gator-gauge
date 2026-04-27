"""
Gator Gauge Occupancy Prediction Model
======================================
Uses Ridge linear regression with cyclical time features (sin/cos encoding of
hour, day-of-week, and month) plus one-hot encoded location to predict
% full at any future date/time/location combo.

Filter assumptions applied before training:
  1. Remove rows where facility is closed (is_closed == True)
  2. Remove impossible occupancy values (percent_full < 0 or > 100)
  3. Remove per-location statistical outliers (> 3 std deviations from location mean)
  4. Restrict to realistic operating hours (5 AM to 11 PM, hours 5-23)
"""

from datetime import date, datetime

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


OPERATING_HOURS = (5, 23)  # 5 AM to 11 PM
OUTLIER_STD_THRESHOLD = 3.0
RIDGE_ALPHA = 1.0

NUMERIC_FEATURES = [
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]
CATEGORICAL_FEATURES = ["location_name"]


def apply_filter_assumptions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Apply all preprocessing filters before model training.
    Returns cleaned DataFrame + a report of how many rows each filter removed.
    """
    report = {}
    original_len = len(df)

    if df.empty:
        report.update(
            {
                "closed_removed": 0,
                "impossible_values_removed": 0,
                "off_hours_removed": 0,
                "outliers_removed": 0,
                "total_removed": 0,
                "final_size": 0,
            }
        )
        return df.copy(), report

    # 1. Remove closed facilities
    before = len(df)
    df = df[df["is_closed"] == False].copy()
    report["closed_removed"] = before - len(df)

    # 2. Remove impossible occupancy values
    before = len(df)
    df = df[(df["percent_full"] >= 0) & (df["percent_full"] <= 100)].copy()
    report["impossible_values_removed"] = before - len(df)

    # 3. Restrict to operating hours (5 AM to 11 PM)
    before = len(df)
    if "hour" in df.columns:
        df = df[(df["hour"] >= OPERATING_HOURS[0]) & (df["hour"] <= OPERATING_HOURS[1])].copy()
    report["off_hours_removed"] = before - len(df)

    # 4. Remove per-location outliers (> 3 std deviations from location mean)
    before = len(df)

    def remove_outliers(group):
        mean = group["percent_full"].mean()
        std = group["percent_full"].std()
        if pd.isna(std) or std == 0:
            return group
        return group[abs(group["percent_full"] - mean) <= OUTLIER_STD_THRESHOLD * std]

    df = df.groupby("location_name", group_keys=False).apply(remove_outliers).reset_index(drop=True)
    report["outliers_removed"] = before - len(df)

    report["total_removed"] = original_len - len(df)
    report["final_size"] = len(df)

    return df, report


def add_cyclical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode time values as sin/cos pairs so the model understands
    that hour 23 is close to hour 0 (cyclical, not linear).
    """
    df = df.copy()

    # Hour of day (0-23)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Day of week (0=Mon, 6=Sun)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week_num"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week_num"] / 7)

    # Month of year (1-12)
    df["month"] = df["pulled_at_local"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    return df


def build_feature_matrix(df: pd.DataFrame):
    """Extract feature matrix X and target y from a preprocessed DataFrame."""
    df = add_cyclical_features(df)
    all_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["percent_full"]
    clean = df[all_cols].dropna()
    X = clean[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = clean["percent_full"]
    return X, y


def train_model(df: pd.DataFrame) -> tuple:
    """
    Train a Ridge regression model on the full dataset.

    Returns:
        pipeline: fitted sklearn Pipeline, ready for predict()
        metrics: dict of MAE, RMSE, R2, sample counts, filter report
        filter_report: what was removed and why
    """
    df_clean, filter_report = apply_filter_assumptions(df)

    if len(df_clean) < 50:
        raise ValueError(
            f"Too few samples after filtering ({len(df_clean)}). "
            "Widen the date range and reload data."
        )

    X, y = build_feature_matrix(df_clean)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", encoder, CATEGORICAL_FEATURES),
        ]
    )

    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("model", Ridge(alpha=RIDGE_ALPHA)),
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    residuals = y_test.values - y_pred

    metrics = {
        "mae":       round(float(mean_absolute_error(y_test, y_pred)), 2),
        "rmse":      round(float(np.sqrt(np.mean(residuals ** 2))), 2),
        "r2":        round(float(r2_score(y_test, y_pred)), 3),
        "n_train":   len(X_train),
        "n_test":    len(X_test),
        "n_locations": df_clean["location_name"].nunique(),
    }

    return pipeline, metrics, filter_report


def _make_row(location: str, hour: int, day_of_week_num: int, month: int) -> pd.DataFrame:
    """Build a single feature row for inference."""
    is_weekend = day_of_week_num >= 5

    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    day_sin = np.sin(2 * np.pi * day_of_week_num / 7)
    day_cos = np.cos(2 * np.pi * day_of_week_num / 7)
    month_sin = np.sin(2 * np.pi * month / 12)
    month_cos = np.cos(2 * np.pi * month / 12)

    return pd.DataFrame(
        [
            {
                "hour_sin": hour_sin,
                "hour_cos": hour_cos,
                "day_sin": day_sin,
                "day_cos": day_cos,
                "month_sin": month_sin,
                "month_cos": month_cos,
                "is_weekend": is_weekend,
                "location_name": location,
            }
        ]
    )


def predict_single(pipeline, location: str, target_datetime: datetime) -> float:
    """
    Predict percent_full for one location at one datetime.
    Returns a value clamped to [0, 100].
    """
    row = _make_row(
        location=location,
        hour=target_datetime.hour,
        day_of_week_num=target_datetime.weekday(),
        month=target_datetime.month,
    )
    raw = pipeline.predict(row)[0]
    return float(np.clip(raw, 0, 100))


def predict_day_curve(pipeline, location: str, target_date: date, rmse: float) -> pd.DataFrame:
    """
    Predict occupancy for all hours of a given day.
    Returns DataFrame with columns: hour, predicted, lower_bound, upper_bound, label.
    """
    day_of_week_num = target_date.weekday()
    month = target_date.month
    records = []

    for hour in range(24):
        row = _make_row(location, hour, day_of_week_num, month)
        raw = pipeline.predict(row)[0]
        pred = float(np.clip(raw, 0, 100))
        records.append(
            {
                "hour": hour,
                "predicted": round(pred, 1),
                "lower_bound": round(float(np.clip(pred - rmse, 0, 100)), 1),
                "upper_bound": round(float(np.clip(pred + rmse, 0, 100)), 1),
            }
        )

    df = pd.DataFrame(records)
    return df


def best_time_to_go(curve_df: pd.DataFrame) -> dict:
    """
    Given a day curve, return the best and worst hours to visit.
    'Best' = lowest predicted occupancy during operating hours.
    """
    operating = curve_df[
        (curve_df["hour"] >= OPERATING_HOURS[0]) &
        (curve_df["hour"] <= OPERATING_HOURS[1])
    ].copy()

    best = operating.loc[operating["predicted"].idxmin()]
    worst = operating.loc[operating["predicted"].idxmax()]

    return {
        "best_hour": int(best["hour"]),
        "best_predicted": best["predicted"],
        "worst_hour": int(worst["hour"]),
        "worst_predicted": worst["predicted"],
    }


def occupancy_label(percent: float) -> tuple[str, str]:
    """Return (label, color) for a given occupancy percentage."""
    if percent < 30:
        return "Not Busy", "green"
    if percent < 60:
        return "Moderate", "orange"
    if percent < 80:
        return "Busy", "darkorange"
    return "Very Busy", "red"
