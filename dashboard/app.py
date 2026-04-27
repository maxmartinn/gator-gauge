from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import charts
import data_access
import model as gym_model
import transforms


st.set_page_config(
    page_title="Gator Gauge - UF Gym Dashboard",
    layout="wide",
)

st.title("Gator Gauge - UF Gym Occupancy Dashboard")
st.caption("Historical trends and Ridge regression occupancy predictions for UF recreational facilities.")


# ── Catalog: locations + available date range ─────────────────────────────────
# Both functions are @st.cache_data(ttl=3600) inside data_access, so this is fast after first run.

all_locations = data_access.get_available_locations()
available_dates = data_access.get_available_dates()

if not all_locations:
    st.error("Cannot reach S3 or no location partitions were found. Check AWS credentials.")
    st.stop()

if not available_dates:
    st.error("No date partitions found under bronze/gym_counts. The bucket may be empty.")
    st.stop()

min_data_date = available_dates[0]
max_data_date = available_dates[-1]
default_start_date = max(min_data_date, max_data_date - timedelta(days=7))


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")
    st.caption(f"S3 data: {min_data_date} → {max_data_date}")

    st.markdown("**Historical Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=default_start_date,
            min_value=min_data_date,
            max_value=max_data_date,
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=max_data_date,
            min_value=min_data_date,
            max_value=max_data_date,
        )

    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()

    st.markdown("**Locations**")
    selected_locations = st.multiselect(
        "Filter locations",
        options=all_locations,
        default=(
            ["SWRC Fitness Total"]
            if "SWRC Fitness Total" in all_locations
            else all_locations[:6]
        ),
    )
    if not selected_locations:
        st.info("Select at least one location to load data.")
        st.stop()

    st.markdown("---")
    st.markdown("**Prediction Model**")
    use_all_for_training = st.checkbox(
        "Train on all locations",
        value=True,
        help="Recommended. More locations give the regression model a stronger baseline.",
    )
    training_start = st.date_input(
        "Training start",
        value=min_data_date,
        min_value=min_data_date,
        max_value=max_data_date,
    )
    training_end = st.date_input(
        "Training end",
        value=max_data_date,
        min_value=min_data_date,
        max_value=max_data_date,
    )
    if training_start > training_end:
        st.error("Training start must be before training end.")
        st.stop()


# ── Data loading helpers ──────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def load_and_preprocess(start: date, end: date, locs: tuple) -> pd.DataFrame:
    """Load from S3 and preprocess. Cached 10 min. Uses tuple for hashable cache key."""
    df = data_access.load_data_from_s3(start, end, list(locs))
    if df.empty:
        return df
    return transforms.preprocess_data(df)


@st.cache_data(ttl=600)
def get_trained_model(start: date, end: date, locs: tuple):
    """Train the Ridge model. Cached per (date-range, locations) combo."""
    df = load_and_preprocess(start, end, locs)
    if df.empty:
        raise ValueError("No data loaded for the selected training range.")
    return gym_model.train_model(df)


# ── Load view data ────────────────────────────────────────────────────────────

with st.spinner("Loading historical data from S3..."):
    df_view = load_and_preprocess(start_date, end_date, tuple(selected_locations))

if df_view.empty:
    st.warning(f"No data found between {start_date} and {end_date} for the selected locations.")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["Historical Analysis", "Predict Occupancy"])


# ═══════════════════════════════════════════════════════════════════
# TAB 1 — Historical Analysis
# ═══════════════════════════════════════════════════════════════════

with tab1:
    if df_view.empty:
        st.info("Adjust the date range or locations in the sidebar to load data.")
    else:
        df_agg = transforms.aggregate_by_hour_location(df_view)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Occupancy", f"{df_view['percent_full'].mean():.1f}%")
        with col2:
            st.metric("Peak Occupancy", f"{df_view['percent_full'].max():.1f}%")
        with col3:
            st.metric("Locations", df_view["location_name"].nunique())
        with col4:
            st.metric("Data Points", f"{len(df_view):,}")

        st.markdown("---")
        st.subheader("Occupancy Over Time")
        st.plotly_chart(
            charts.line_chart_occupancy(df_agg, selected_locations),
            use_container_width=True,
        )

        st.subheader("Busiest Times: Hour × Day of Week")
        st.caption("Red = crowded · Green = quiet · All times Eastern")
        st.plotly_chart(charts.heatmap_hourly_occupancy(df_view), use_container_width=True)

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.subheader("Average Occupancy by Facility")
            st.plotly_chart(charts.bar_chart_by_facility(df_view), use_container_width=True)
        with col_b:
            st.subheader("Top 10 Busiest Slots")
            peak_table = charts.peak_hours_table(df_view, top_n=10)
            st.dataframe(peak_table, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 2 — Predict Occupancy
# ═══════════════════════════════════════════════════════════════════

with tab2:
    training_locations = all_locations if use_all_for_training else selected_locations

    with st.spinner("Training Ridge regression model from S3 data..."):
        try:
            pipeline, metrics, filter_report = get_trained_model(
                training_start,
                training_end,
                tuple(training_locations),
            )
        except Exception as exc:
            st.error(f"Model could not be trained: {exc}")
            st.stop()

    with st.expander("Model Details and Training Report", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("R² Score", metrics["r2"])
        with col_b:
            st.metric("Mean Abs Error", f"±{metrics['mae']}%")
        with col_c:
            st.metric("RMSE", f"±{metrics['rmse']}%")

        st.markdown(
            f"Trained on **{metrics['n_train']:,}** samples · "
            f"tested on **{metrics['n_test']:,}** held-out samples · "
            f"**{metrics['n_locations']}** locations."
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Closed removed", filter_report["closed_removed"])
        with col2:
            st.metric("Impossible values", filter_report["impossible_values_removed"])
        with col3:
            st.metric("Off-hours removed", filter_report["off_hours_removed"])
        with col4:
            st.metric("Outliers removed", filter_report["outliers_removed"])

        st.info(
            "Model: Ridge Linear Regression. "
            "Features: cyclical hour, cyclical day-of-week, cyclical month, "
            "weekend flag, one-hot location. "
            "Predictions are estimates, not live counts."
        )

    st.markdown("---")
    st.subheader("Predict Occupancy at a Specific Time")

    col_loc, col_date, col_hour = st.columns([2, 1, 1])
    with col_loc:
        pred_location = st.selectbox("Location", options=all_locations, index=0)
    with col_date:
        pred_date = st.date_input(
            "Date",
            value=date.today(),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=30),
        )
    with col_hour:
        pred_hour = st.slider("Hour (Eastern)", min_value=5, max_value=23, value=14, format="%d:00")

    pred_dt = datetime(pred_date.year, pred_date.month, pred_date.day, pred_hour)
    predicted_pct = gym_model.predict_single(pipeline, pred_location, pred_dt)
    badge_label, badge_color = gym_model.occupancy_label(predicted_pct)

    col_gauge, col_detail = st.columns([1, 2])

    with col_gauge:
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=predicted_pct,
                number={"suffix": "%", "font": {"size": 40}},
                title={
                    "text": (
                        f"{pred_location}<br>"
                        f"<span style='font-size:18px'>"
                        f"{pred_date.strftime('%A, %b %d')} at {pred_hour}:00"
                        f"</span>"
                    )
                },
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {"color": badge_color},
                    "steps": [
                        {"range": [0, 30],  "color": "#d4f1d4"},
                        {"range": [30, 60], "color": "#fff3cd"},
                        {"range": [60, 80], "color": "#ffe5cc"},
                        {"range": [80, 100],"color": "#f8d7da"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 3},
                        "thickness": 0.75,
                        "value": predicted_pct,
                    },
                },
            )
        )
        fig_gauge.update_layout(height=280, margin=dict(t=60, b=20, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.markdown(
            f"<h3 style='text-align:center; color:{badge_color}'>{badge_label}</h3>",
            unsafe_allow_html=True,
        )
        st.caption(f"Confidence band: ±{metrics['rmse']}% (model RMSE)")

    with col_detail:
        st.markdown(f"**Predicted occupancy all day — {pred_date.strftime('%A, %B %d')}**")
        curve_df = gym_model.predict_day_curve(pipeline, pred_location, pred_date, metrics["rmse"])
        rec = gym_model.best_time_to_go(curve_df)

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            best_label, _ = gym_model.occupancy_label(rec["best_predicted"])
            st.success(
                f"**Best time to go:** {rec['best_hour']}:00\n\n"
                f"Predicted {rec['best_predicted']:.1f}% full — {best_label}"
            )
        with bcol2:
            worst_label, _ = gym_model.occupancy_label(rec["worst_predicted"])
            st.error(
                f"**Avoid:** {rec['worst_hour']}:00\n\n"
                f"Predicted {rec['worst_predicted']:.1f}% full — {worst_label}"
            )

        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=list(curve_df["hour"]) + list(curve_df["hour"])[::-1],
            y=list(curve_df["upper_bound"]) + list(curve_df["lower_bound"])[::-1],
            fill="toself",
            fillcolor="rgba(99,110,250,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name=f"±{metrics['rmse']}% band",
            hoverinfo="skip",
        ))
        fig_curve.add_trace(go.Scatter(
            x=curve_df["hour"],
            y=curve_df["predicted"],
            mode="lines+markers",
            name="Predicted % full",
            line=dict(color="rgb(99,110,250)", width=2),
            marker=dict(size=6),
        ))
        fig_curve.add_vline(
            x=rec["best_hour"], line_dash="dot", line_color="green",
            annotation_text="Best", annotation_position="top",
        )
        fig_curve.add_vline(
            x=rec["worst_hour"], line_dash="dot", line_color="red",
            annotation_text="Avoid", annotation_position="top",
        )
        if pred_date == date.today():
            fig_curve.add_vline(
                x=datetime.now().hour, line_dash="dash", line_color="gray",
                annotation_text="Now", annotation_position="bottom",
            )
        fig_curve.update_layout(
            height=270,
            margin=dict(t=20, b=40, l=10, r=10),
            xaxis=dict(title="Hour of day (Eastern)", tickmode="linear", dtick=2),
            yaxis=dict(title="% Full", range=[0, 100]),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("---")
    st.subheader(f"All Locations at {pred_hour}:00 on {pred_date.strftime('%A, %b %d')}")
    st.caption("Find the quietest option at your target time.")

    all_preds = []
    for loc in all_locations:
        pct = gym_model.predict_single(pipeline, loc, pred_dt)
        label, _ = gym_model.occupancy_label(pct)
        all_preds.append({"Location": loc, "Predicted % Full": round(pct, 1), "Status": label})

    preds_df = pd.DataFrame(all_preds).sort_values("Predicted % Full")
    fig_all = px.bar(
        preds_df,
        x="Predicted % Full",
        y="Location",
        orientation="h",
        color="Predicted % Full",
        color_continuous_scale=["green", "yellow", "orange", "red"],
        range_color=[0, 100],
        text="Predicted % Full",
    )
    fig_all.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_all.update_layout(
        height=550,
        margin=dict(t=10, b=10, l=10, r=80),
        coloraxis_showscale=False,
        xaxis=dict(range=[0, 110], title="Predicted Occupancy (%)"),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_all, use_container_width=True)


st.markdown("---")
st.caption(
    "Gator Gauge | S3 data from UF Rec Services | "
    "Ridge regression estimates | All times in America/New_York"
)
