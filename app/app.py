from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# PAGE CONFIGURATION

st.set_page_config(
    page_title="Elevate",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# PROJECT PATHS

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DAILY_FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "daily_features.csv"
)

PERFORMANCE_FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "performance_features.csv"
)

QUALITY_REPORT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "data_quality_report.csv"
)


# CUSTOM STYLING

st.html(
    """
    <style>
        .block-container {
            padding-top: 4rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 14px;
            padding: 16px;
        }

        .recommendation-card {
            border-radius: 16px;
            padding: 20px;
            margin-top: 8px;
            margin-bottom: 18px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background-color: rgba(255, 255, 255, 0.04);
        }

        .recommendation-title {
            font-size: 1.45rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .recommendation-reason {
            font-size: 1rem;
            opacity: 0.85;
        }

        .small-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.06rem;
            opacity: 0.65;
            margin-bottom: 4px;
        }

        .section-subtitle {
            opacity: 0.72;
            margin-top: -8px;
            margin-bottom: 18px;
        }
    </style>
    """
)


# DATA LOADING

@st.cache_data
def load_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Load processed Elevate feature files.
    """

    required_files = [
        DAILY_FEATURES_PATH,
        PERFORMANCE_FEATURES_PATH,
        QUALITY_REPORT_PATH,
    ]

    missing_files = [
        path
        for path in required_files
        if not path.exists()
    ]

    if missing_files:
        missing_text = "\n".join(
            str(path)
            for path in missing_files
        )

        raise FileNotFoundError(
            "Required processed files were not found:\n"
            f"{missing_text}\n\n"
            "Run python src/etl_pipeline.py first."
        )

    daily = pd.read_csv(
        DAILY_FEATURES_PATH,
        parse_dates=["log_date"],
    )

    performance = pd.read_csv(
        PERFORMANCE_FEATURES_PATH,
        parse_dates=[
            "test_date",
            "previous_session_date",
        ],
    )

    quality = pd.read_csv(
        QUALITY_REPORT_PATH,
    )

    return daily, performance, quality


# HELPER FUNCTIONS

def safe_delta(
    current_value: float | int | None,
    previous_value: float | int | None,
    decimals: int = 1,
) -> str | None:
    """
    Return a formatted metric delta when both values exist.
    """

    if pd.isna(current_value) or pd.isna(previous_value):
        return None

    difference = current_value - previous_value

    return f"{difference:+.{decimals}f}"


def get_latest_metric(
    dataframe: pd.DataFrame,
    metric_name: str,
) -> tuple[float | None, float | None]:
    """
    Return the latest and previous value for a performance metric.
    """

    metric_data = (
        dataframe.loc[
            dataframe["metric_name"] == metric_name
        ]
        .sort_values("test_date")
    )

    if metric_data.empty:
        return None, None

    latest_value = metric_data.iloc[-1]["metric_value"]

    previous_value = (
        metric_data.iloc[-2]["metric_value"]
        if len(metric_data) >= 2
        else None
    )

    return latest_value, previous_value


def get_personal_best(
    dataframe: pd.DataFrame,
    metric_name: str,
) -> float | None:
    """
    Return the best recorded value for a performance metric.
    """

    metric_data = dataframe.loc[
        dataframe["metric_name"] == metric_name,
        "metric_value",
    ]

    if metric_data.empty:
        return None

    return float(metric_data.max())


def format_metric_value(
    value: float | int | None,
    unit: str = "in",
    decimals: int = 1,
) -> str:
    """
    Format a dashboard metric safely.
    """

    if value is None or pd.isna(value):
        return "No data"

    return f"{value:.{decimals}f} {unit}"


def build_recommendation_action(
    recommendation: str,
) -> str:
    """
    Translate recommendation status into an actionable message.
    """

    action_map = {
        "Train Hard": (
            "Proceed with the planned session and maintain "
            "normal training volume and intensity."
        ),
        "Modify Training": (
            "Reduce lower-body volume or intensity. Prioritize "
            "quality, technique, or upper-body training."
        ),
        "Prioritize Recovery": (
            "Avoid hard lower-body work. Prioritize rest, "
            "mobility, light recovery, and pain monitoring."
        ),
    }

    return action_map.get(
        recommendation,
        "Review the available recovery data before training.",
    )


def calculate_data_completeness(
    daily: pd.DataFrame,
) -> float:
    """
    Calculate completeness for the primary readiness fields.
    """

    required_columns = [
        "sleep_hours",
        "sleep_quality_1_5",
        "soreness_overall_1_10",
        "energy_1_5",
        "stress_1_5",
        "motivation_1_5",
    ]

    available_columns = [
        column
        for column in required_columns
        if column in daily.columns
    ]

    if not available_columns or daily.empty:
        return 0.0

    completed_values = (
        daily[available_columns]
        .notna()
        .sum()
        .sum()
    )

    expected_values = (
        len(daily)
        * len(available_columns)
    )

    return (
        completed_values
        / expected_values
        * 100
    )


# LOAD DATA

try:
    daily_features, performance_features, quality_report = (
        load_data()
    )
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()


# SIDEBAR FILTERS

st.sidebar.title("Elevate")
st.sidebar.caption(
    "Sports performance analytics for smarter training decisions"
)

athlete_ids = sorted(
    daily_features["athlete_id"]
    .dropna()
    .unique()
    .tolist()
)

selected_athlete = st.sidebar.selectbox(
    "Athlete",
    options=athlete_ids,
    index=0,
)

athlete_daily = (
    daily_features.loc[
        daily_features["athlete_id"]
        == selected_athlete
    ]
    .copy()
    .sort_values("log_date")
)

athlete_performance = (
    performance_features.loc[
        performance_features["athlete_id"]
        == selected_athlete
    ]
    .copy()
    .sort_values("test_date")
)

minimum_date = athlete_daily["log_date"].min().date()
maximum_date = athlete_daily["log_date"].max().date()

selected_date_range = st.sidebar.date_input(
    "Date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

if (
    isinstance(selected_date_range, tuple)
    and len(selected_date_range) == 2
):
    start_date, end_date = selected_date_range
else:
    start_date = minimum_date
    end_date = maximum_date

filtered_daily = athlete_daily.loc[
    athlete_daily["log_date"]
    .dt.date
    .between(start_date, end_date)
].copy()

filtered_performance = athlete_performance.loc[
    athlete_performance["test_date"]
    .dt.date
    .between(start_date, end_date)
].copy()

metric_options = (
    athlete_performance["metric_name"]
    .dropna()
    .sort_values()
    .unique()
    .tolist()
)

default_metric = (
    "approach_vertical"
    if "approach_vertical" in metric_options
    else metric_options[0]
)

selected_metric = st.sidebar.selectbox(
    "Performance metric",
    options=metric_options,
    index=metric_options.index(default_metric),
)

st.sidebar.divider()

st.sidebar.markdown(
    """
    **Version 1 scope**

    - Single-athlete decision support
    - Training and recovery analytics
    - Explainable recommendations
    - Synthetic demonstration data
    """
)


# PAGE HEADER

st.title("Elevate Performance Overview")

st.markdown(
    """
    <div class="section-subtitle">
        Monitor performance, recovery, and training load in one
        decision-focused dashboard.
    </div>
    """,
    unsafe_allow_html=True,
)


# LATEST STATUS

if filtered_daily.empty:
    st.warning(
        "No daily recovery data exists for the selected date range."
    )
    st.stop()

latest_daily = filtered_daily.iloc[-1]

previous_daily = (
    filtered_daily.iloc[-2]
    if len(filtered_daily) >= 2
    else None
)

latest_approach, previous_approach = get_latest_metric(
    filtered_performance,
    "approach_vertical",
)

latest_standing, previous_standing = get_latest_metric(
    filtered_performance,
    "standing_vertical",
)

approach_personal_best = get_personal_best(
    athlete_performance,
    "approach_vertical",
)

data_completeness = calculate_data_completeness(
    filtered_daily
)


# PRIMARY KPI CARDS

kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4 = (
    st.columns(4)
)

with kpi_col_1:
    st.metric(
        label="Current Approach Vertical",
        value=format_metric_value(
            latest_approach,
            unit="in",
        ),
        delta=safe_delta(
            latest_approach,
            previous_approach,
        ),
    )

with kpi_col_2:
    st.metric(
        label="Approach Personal Best",
        value=format_metric_value(
            approach_personal_best,
            unit="in",
        ),
    )

with kpi_col_3:
    st.metric(
        label="Current Readiness",
        value=f"{latest_daily['readiness_score']:.1f}/100",
        delta=safe_delta(
            latest_daily["readiness_score"],
            (
                previous_daily["readiness_score"]
                if previous_daily is not None
                else None
            ),
        ),
    )

with kpi_col_4:
    st.metric(
        label="7-Day Training Load",
        value=f"{latest_daily['seven_day_training_load']:.0f}",
        delta=safe_delta(
            latest_daily["seven_day_training_load"],
            (
                previous_daily["seven_day_training_load"]
                if previous_daily is not None
                else None
            ),
            decimals=0,
        ),
        delta_color="inverse",
    )


# RECOMMENDATION CARD

recommendation = latest_daily["recommendation"]
recommendation_reason = latest_daily[
    "recommendation_reason"
]
recommended_action = build_recommendation_action(
    recommendation
)

recommendation_html = f"""
<div class="recommendation-card">
    <div class="small-label">
        Latest training recommendation
    </div>

    <div class="recommendation-title">
        {recommendation}
    </div>

    <div class="recommendation-reason">
        <strong>Reason:</strong> {recommendation_reason}<br>
        <strong>Action:</strong> {recommended_action}
    </div>
</div>
"""

st.html(
    recommendation_html,
    width="stretch",
)


# SECONDARY KPI CARDS

secondary_col_1, secondary_col_2, secondary_col_3, secondary_col_4 = (
    st.columns(4)
)

with secondary_col_1:
    st.metric(
        label="Sleep",
        value=f"{latest_daily['sleep_hours']:.1f} hrs",
    )

with secondary_col_2:
    st.metric(
        label="Overall Soreness",
        value=f"{latest_daily['soreness_overall_1_10']:.0f}/10",
        delta_color="inverse",
    )

with secondary_col_3:
    st.metric(
        label="Energy",
        value=f"{latest_daily['energy_1_5']:.0f}/5",
    )

with secondary_col_4:
    st.metric(
        label="Data Completeness",
        value=f"{data_completeness:.1f}%",
    )


# PERFORMANCE TREND CHART

st.subheader("Performance Trend")

selected_performance = (
    filtered_performance.loc[
        filtered_performance["metric_name"]
        == selected_metric
    ]
    .copy()
    .sort_values("test_date")
)

if selected_performance.empty:
    st.info(
        "No performance data is available for the selected metric "
        "and date range."
    )
else:
    performance_figure = go.Figure()

    performance_figure.add_trace(
        go.Scatter(
            x=selected_performance["test_date"],
            y=selected_performance["metric_value"],
            mode="lines+markers",
            name="Test result",
            hovertemplate=(
                "Date: %{x|%b %d, %Y}"
                "<br>Result: %{y:.1f}"
                "<extra></extra>"
            ),
        )
    )

    performance_figure.add_trace(
        go.Scatter(
            x=selected_performance["test_date"],
            y=selected_performance[
                "three_test_rolling_average"
            ],
            mode="lines",
            name="3-test rolling average",
            line={
                "dash": "dash",
            },
            hovertemplate=(
                "Date: %{x|%b %d, %Y}"
                "<br>Rolling average: %{y:.1f}"
                "<extra></extra>"
            ),
        )
    )

    performance_figure.update_layout(
        height=420,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        xaxis_title="Date",
        yaxis_title="Performance",
        legend_title=None,
        hovermode="x unified",
    )

    st.plotly_chart(
        performance_figure,
        width="stretch",
    )


# READINESS AND TRAINING LOAD

chart_col_1, chart_col_2 = st.columns(2)

with chart_col_1:
    st.subheader("Readiness Trend")

    readiness_figure = px.line(
        filtered_daily,
        x="log_date",
        y="readiness_score",
        markers=True,
    )

    readiness_figure.add_hline(
        y=70,
        line_dash="dash",
        annotation_text="Train hard threshold",
    )

    readiness_figure.add_hline(
        y=50,
        line_dash="dash",
        annotation_text="Recovery threshold",
    )

    readiness_figure.update_layout(
        height=380,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        xaxis_title="Date",
        yaxis_title="Readiness score",
        showlegend=False,
    )

    st.plotly_chart(
        readiness_figure,
        width="stretch",
    )

with chart_col_2:
    st.subheader("Recent Training Load")

    load_data = filtered_daily[
        [
            "log_date",
            "daily_training_load",
            "seven_day_training_load",
        ]
    ].copy()

    load_figure = go.Figure()

    load_figure.add_trace(
        go.Bar(
            x=load_data["log_date"],
            y=load_data["daily_training_load"],
            name="Daily load",
        )
    )

    load_figure.add_trace(
        go.Scatter(
            x=load_data["log_date"],
            y=load_data["seven_day_training_load"],
            mode="lines",
            name="7-day load",
            yaxis="y2",
        )
    )

    load_figure.update_layout(
        height=380,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        xaxis_title="Date",
        yaxis={
            "title": "Daily load",
        },
        yaxis2={
            "title": "7-day load",
            "overlaying": "y",
            "side": "right",
        },
        legend_title=None,
    )

    st.plotly_chart(
        load_figure,
        width="stretch",
    )


# SIGNAL SUMMARY

st.subheader("Current Signals")

signal_col_1, signal_col_2, signal_col_3 = (
    st.columns(3)
)

with signal_col_1:
    sleep_status = (
        "Adequate"
        if latest_daily["sleep_hours"] >= 7
        else "Below target"
    )

    st.markdown(
        f"""
        **Sleep status:** {sleep_status}

        Latest sleep: `{latest_daily['sleep_hours']:.1f} hours`
        """
    )

with signal_col_2:
    soreness_status = (
        "High"
        if latest_daily["soreness_overall_1_10"] >= 7
        else "Manageable"
    )

    st.markdown(
        f"""
        **Soreness status:** {soreness_status}

        Latest soreness:
        `{latest_daily['soreness_overall_1_10']:.0f}/10`
        """
    )

with signal_col_3:
    load_spike_ratio = latest_daily["load_spike_ratio"]

    if pd.isna(load_spike_ratio):
        load_status = "Insufficient history"
        load_value = "N/A"
    else:
        load_status = (
            "Elevated"
            if load_spike_ratio >= 1.5
            else "Normal"
        )
        load_value = f"{load_spike_ratio:.2f}"

    st.markdown(
        f"""
        **Load status:** {load_status}

        Load spike ratio: `{load_value}`
        """
    )


# DATA QUALITY SUMMARY

with st.expander("Data quality summary"):
    st.dataframe(
        quality_report,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Missing optional values may appear in this report. "
        "Duplicate identifiers and invalid dates should remain zero."
    )