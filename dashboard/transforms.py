import pandas as pd
# Map day of week to names
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess gym data:
    - Parse timestamps to UTC datetime
    - Convert to America/New_York timezone (UF time)
    - Extract hour, day_of_week, date
    - Remove closed facilities
    """
    if df.empty:
        return df

    df = df.copy()

    # Parse timestamps to UTC
    df["pulled_at_utc"] = pd.to_datetime(df["pulled_at_utc"], utc=True, errors="coerce")
    df["last_updated_source_time"] = pd.to_datetime(
        df["last_updated_source_time"], utc=True, errors="coerce"
    )

    # Convert to America/New_York (UF is in Eastern time)
    eastern = "America/New_York"
    df["pulled_at_local"] = df["pulled_at_utc"].dt.tz_convert(eastern)

    # Extract time features (in local time)
    df["date"] = df["pulled_at_local"].dt.date
    df["hour"] = df["pulled_at_local"].dt.hour
    df["day_of_week_num"] = df["pulled_at_local"].dt.dayofweek  # 0=Mon, 6=Sun
    df["day_of_week"] = df["day_of_week_num"].map(lambda x: DAY_NAMES[x])
    df["is_weekend"] = df["day_of_week_num"].isin([5, 6])

    # Filter out closed facilities for occupancy analysis
    df = df[df["is_closed"] == False].copy()

    return df


def aggregate_by_hour_location(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate data by hour and location (in case there are multiple readings per hour).
    Takes average of percent_full and last_count.
    """
    if df.empty:
        return df

    agg_dict = {
        "last_count": "mean",
        "total_capacity": "first",
        "percent_full": "mean",
        "facility_name": "first",
    }

    grouped = (
        df.groupby(["pulled_at_local", "location_name", "hour", "day_of_week", "date"])
        .agg(agg_dict)
        .reset_index()
    )

    # Round percentages
    grouped["percent_full"] = grouped["percent_full"].round(2)
    grouped["last_count"] = grouped["last_count"].round(0).astype(int)

    return grouped


def aggregate_by_hour_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate across all locations by hour and day_of_week.
    Useful for heatmap: shows average occupancy by hour x day.
    """
    if df.empty:
        return df

    heatmap_data = (
        df.groupby(["hour", "day_of_week"])
        .agg({"percent_full": "mean", "last_count": "mean"})
        .reset_index()
    )

    heatmap_data["percent_full"] = heatmap_data["percent_full"].round(2)
    heatmap_data["last_count"] = heatmap_data["last_count"].round(0).astype(int)

    # Add day_of_week_num for sorting
    heatmap_data["day_of_week_num"] = heatmap_data["day_of_week"].map(
        {name: i for i, name in enumerate(DAY_NAMES)}
    )
    heatmap_data = heatmap_data.sort_values(["day_of_week_num", "hour"])

    return heatmap_data
