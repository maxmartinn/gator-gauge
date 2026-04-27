import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import transforms

GAP_THRESHOLD = pd.Timedelta(hours=3)


def format_hour(hour: int) -> str:
    """Return a compact 12-hour label for an integer hour."""
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour} {suffix}"


def _insert_gap_breaks(df: pd.DataFrame) -> pd.DataFrame:
    """Insert NaN rows wherever consecutive samples are more than GAP_THRESHOLD apart.

    Plotly draws straight lines across NaN-free gaps; inserting a NaN forces a break
    so the chart honestly shows missing data instead of interpolating across it.
    """
    if df.empty:
        return df
    pieces = []
    for _, group in df.sort_values("pulled_at_local").groupby("location_name", sort=False):
        gaps = group["pulled_at_local"].diff() > GAP_THRESHOLD
        if not gaps.any():
            pieces.append(group)
            continue
        breaks = group.loc[gaps].copy()
        breaks["pulled_at_local"] = breaks["pulled_at_local"] - GAP_THRESHOLD / 2
        for col in ("percent_full", "last_count", "total_capacity"):
            if col in breaks.columns:
                breaks[col] = np.nan
        pieces.append(pd.concat([group, breaks]).sort_values("pulled_at_local"))
    return pd.concat(pieces, ignore_index=True)


def line_chart_occupancy(
    df: pd.DataFrame,
    locations: list = None,
    show_occupancy: bool = True,
    show_count: bool = False,
    show_capacity: bool = False,
) -> go.Figure:
    """
    Create a line chart showing any selected mix of occupancy %, people count, and max occupancy.
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

    if not any([show_occupancy, show_count, show_capacity]):
        fig = go.Figure()
        fig.add_annotation(
            text="Select at least one chart line in the sidebar",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    plot_df = _insert_gap_breaks(plot_df)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    has_percent_axis = show_occupancy or (show_capacity and not show_count)
    has_count_axis = show_count or (show_capacity and show_count)

    for idx, (location, group) in enumerate(plot_df.groupby("location_name", sort=False)):
        color = colors[idx % len(colors)]

        if show_occupancy:
            fig.add_trace(
                go.Scatter(
                    x=group["pulled_at_local"],
                    y=group["percent_full"],
                    mode="lines",
                    name=f"{location} occupancy",
                    legendgroup=location,
                    line=dict(color=color),
                    customdata=group[["last_count", "total_capacity"]],
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "%{x|%b %d, %I:%M %p}<br>"
                        "Occupancy: %{y:.1f}%<br>"
                        "Count: %{customdata[0]:.0f}<br>"
                        "Capacity: %{customdata[1]:.0f}<extra></extra>"
                    ),
                )
            )

        if show_count:
            fig.add_trace(
                go.Scatter(
                    x=group["pulled_at_local"],
                    y=group["last_count"],
                    mode="lines",
                    name=f"{location} count",
                    legendgroup=location,
                    line=dict(
                        color=color,
                        dash="dot" if show_occupancy else "solid",
                    ),
                    yaxis="y2" if has_percent_axis else "y",
                    customdata=group[["percent_full", "total_capacity"]],
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "%{x|%b %d, %I:%M %p}<br>"
                        "Count: %{y:.0f}<br>"
                        "Occupancy: %{customdata[0]:.1f}%<br>"
                        "Capacity: %{customdata[1]:.0f}<extra></extra>"
                    ),
                )
            )

        if show_capacity:
            capacity_y = (
                np.where(group["total_capacity"].notna(), 100, np.nan)
                if not show_count
                else group["total_capacity"]
            )
            capacity_axis = "y2" if has_percent_axis and show_count else "y"
            capacity_label = "max %" if not show_count else "max occupancy"
            fig.add_trace(
                go.Scatter(
                    x=group["pulled_at_local"],
                    y=capacity_y,
                    mode="lines",
                    name=f"{location} {capacity_label}",
                    legendgroup=location,
                    line=dict(color=color, dash="dash"),
                    yaxis=capacity_axis,
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "%{x|%b %d, %I:%M %p}<br>"
                        "Max occupancy: %{y:.0f}<extra></extra>"
                    ),
                )
            )

    title_parts = []
    if show_occupancy:
        title_parts.append("Occupancy")
    if show_count:
        title_parts.append("People Count")
    if show_capacity:
        title_parts.append("Max Occupancy")

    yaxis_title = "Occupancy (%)" if has_percent_axis else "People Count"
    layout_updates = dict(
        title=" and ".join(title_parts) + " Over Time",
        height=400,
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        xaxis_title="Time (Eastern)",
        xaxis=dict(tickformat="%b %d<br>%I %p"),
        yaxis=dict(title=yaxis_title),
    )

    if has_percent_axis:
        layout_updates["yaxis"]["ticksuffix"] = "%"
        layout_updates["yaxis"]["rangemode"] = "tozero"

    if has_percent_axis and has_count_axis:
        layout_updates["yaxis2"] = dict(
            title="People Count",
            overlaying="y",
            side="right",
            rangemode="tozero",
        )
    elif has_count_axis:
        layout_updates["yaxis"]["rangemode"] = "tozero"

    fig.update_layout(**layout_updates)

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
    hour_values = list(pivot.columns)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=hour_values,
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
        xaxis=dict(
            tickmode="array",
            tickvals=hour_values,
            ticktext=[format_hour(hour) for hour in hour_values],
        ),
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

    table = (
        df.groupby(["hour", "day_of_week", "location_name"])
        .agg({"percent_full": "mean"})
        .reset_index()
        .nlargest(top_n, "percent_full")
        .round(2)
        .rename(columns={"percent_full": "Avg % Full"})
    )
    table["Hour"] = table["hour"].map(format_hour)
    return table[["Hour", "day_of_week", "location_name", "Avg % Full"]]
