import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import transforms


def line_chart_occupancy(df: pd.DataFrame, locations: list = None) -> go.Figure:
    """
    Create a line chart showing % full over time for selected locations.
    If locations is None, shows all locations in df.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    if locations:
        plot_df = df[df["location_name"].isin(locations)]
    else:
        plot_df = df

    fig = px.line(
        plot_df.sort_values("pulled_at_local"),
        x="pulled_at_local",
        y="percent_full",
        color="location_name",
        title="Occupancy Over Time (%)",
        labels={
            "pulled_at_local": "Time (Eastern)",
            "percent_full": "Occupancy (%)",
            "location_name": "Location",
        },
    )

    fig.update_layout(
        height=400,
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def heatmap_hourly_occupancy(df: pd.DataFrame) -> go.Figure:
    """
    Create a heatmap showing average % full by hour x day_of_week.
    Great for answering "when is it busiest?"
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    # Aggregate by hour and day
    heatmap_data = transforms.aggregate_by_hour_day(df)

    # Pivot to get day x hour matrix
    pivot = heatmap_data.pivot_table(
        values="percent_full", index="day_of_week", columns="hour", aggfunc="mean"
    )

    # Reorder rows to Monday=top, Sunday=bottom
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdYlGn_r",  # Red=busy, Green=empty
            text=pivot.values.round(1),
            texttemplate="%{text:.1f}%",
            textfont={"size": 10},
            colorbar=dict(title="Avg %<br>Full"),
        )
    )

    fig.update_layout(
        title="Average Occupancy by Hour x Day of Week",
        xaxis_title="Hour of Day (Eastern)",
        yaxis_title="Day of Week",
        height=400,
    )

    return fig


def bar_chart_by_facility(df: pd.DataFrame) -> go.Figure:
    """
    Create a bar chart comparing average occupancy by facility.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    facility_avg = (
        df.groupby("facility_name")
        .agg({"percent_full": "mean", "last_count": "mean", "total_capacity": "first"})
        .reset_index()
        .sort_values("percent_full", ascending=False)
    )

    fig = px.bar(
        facility_avg,
        x="facility_name",
        y="percent_full",
        title="Average Occupancy by Facility (%)",
        labels={"facility_name": "Facility", "percent_full": "Avg Occupancy (%)"},
        text="percent_full",
    )

    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        height=350,
        xaxis_tickangle=-45,
    )

    return fig


def peak_hours_table(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Return a table of the top N busiest hour x location combinations.
    """
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(["hour", "day_of_week", "location_name"])
        .agg({"percent_full": "mean"})
        .reset_index()
        .nlargest(top_n, "percent_full")
        .round(2)
        .rename(columns={"percent_full": "Avg % Full"})
    )
