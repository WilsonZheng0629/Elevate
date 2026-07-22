from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Elevate | Recovery",
    page_icon="🫀",
    layout="wide",
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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


# ============================================================
# STYLING
# ============================================================

st.html(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 14px;
            padding: 16px;
        }

        .recovery-card {
            border-radius: 14px;
            padding: 18px;
            margin-top: 8px;
            margin-bottom: 16px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background-color: rgba(255, 255, 255, 0.04);
        }

        .recovery-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .recovery-text {
            line-height: 1.5;
            opacity: 0.88;
        }
    </style>
    """
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    required_files = [
        DAILY_FEATURES_PATH,
        PERFORMANCE_FEATURES_PATH,
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

    return daily, performance


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_correlation(
    dataframe: pd.DataFrame,
    x_column: str,
    y_column: str,
) -> tuple[float | None, int]:
    """
    Calculate Pearson correlation after removing missing values.
    """

    clean = dataframe[
        [
            x_column,
            y_column,
        ]
    ].dropna()

    sample_size = len(clean)

    if sample_size < 3:
        return None, sample_size

    correlation = clean[
        x_column
    ].corr(
        clean[y_column]
    )

    if pd.isna(correlation):
        return None, sample_size

    return float(correlation), sample_size


def correlation_label(
    correlation: float | None,
) -> str:
    """
    Convert a correlation value into a readable description.
    """

    if correlation is None:
        return "Insufficient data"

    absolute_value = abs(correlation)

    if absolute_value < 0.20:
        strength = "very weak"
    elif absolute_value < 0.40:
        strength = "weak"
    elif absolute_value < 0.60:
        strength = "moderate"
    elif absolute_value < 0.80:
        strength = "strong"
    else:
        strength = "very strong"

    direction = (
        "positive"
        if correlation > 0
        else "negative"
    )

    return f"{strength} {direction}"


def build_recovery_action(
    recommendation: str,
) -> str:
    actions = {
        "Train Hard": (
            "Recovery indicators support the planned session."
        ),
        "Modify Training": (
            "Reduce lower-body volume or intensity and preserve "
            "movement quality."
        ),
        "Prioritize Recovery": (
            "Avoid hard lower-body work and prioritize rest, "
            "mobility, and pain monitoring."
        ),
    }

    return actions.get(
        recommendation,
        "Review the available recovery information.",
    )


def create_soreness_group(
    soreness: pd.Series,
) -> pd.Series:
    return pd.cut(
        soreness,
        bins=[
            -np.inf,
            3,
            6,
            np.inf,
        ],
        labels=[
            "Low soreness (1–3)",
            "Moderate soreness (4–6)",
            "High soreness (7–10)",
        ],
    )


# ============================================================
# LOAD DATA
# ============================================================

try:
    daily_features, performance_features = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()


# ============================================================
# HEADER
# ============================================================

st.title("Recovery and Readiness")

st.caption(
    "Analyze sleep, soreness, readiness, pain, and training load "
    "to support daily training decisions."
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================

athlete_ids = sorted(
    daily_features["athlete_id"]
    .dropna()
    .unique()
    .tolist()
)

selected_athlete = st.sidebar.selectbox(
    "Athlete",
    options=athlete_ids,
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

if athlete_daily.empty:
    st.warning(
        "No wellness data is available for the selected athlete."
    )
    st.stop()

minimum_date = athlete_daily["log_date"].min().date()
maximum_date = athlete_daily["log_date"].max().date()

selected_date_range = st.sidebar.date_input(
    "Date range",
    value=(
        minimum_date,
        maximum_date,
    ),
    min_value=minimum_date,
    max_value=maximum_date,
)

if (
    isinstance(selected_date_range, tuple)
    and len(selected_date_range) == 2
):
    start_date, end_date = selected_date_range
else:
    start_date, end_date = minimum_date, maximum_date

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
    format_func=lambda value: (
        value.replace("_", " ").title()
    ),
)

filtered_daily = athlete_daily.loc[
    athlete_daily["log_date"]
    .dt.date
    .between(
        start_date,
        end_date,
    )
].copy()

filtered_performance = athlete_performance.loc[
    (
        athlete_performance["test_date"]
        .dt.date
        .between(
            start_date,
            end_date,
        )
    )
    &
    (
        athlete_performance["metric_name"]
        == selected_metric
    )
].copy()

if filtered_daily.empty:
    st.warning(
        "No recovery data matches the selected filters."
    )
    st.stop()


# ============================================================
# LATEST STATUS
# ============================================================

latest = filtered_daily.iloc[-1]

previous = (
    filtered_daily.iloc[-2]
    if len(filtered_daily) >= 2
    else None
)

readiness_delta = (
    latest["readiness_score"]
    - previous["readiness_score"]
    if previous is not None
    else None
)

average_sleep = float(
    filtered_daily["sleep_hours"].mean()
)

average_soreness = float(
    filtered_daily[
        "soreness_overall_1_10"
    ].mean()
)

low_readiness_days = int(
    (
        filtered_daily["readiness_score"]
        < 50
    ).sum()
)

pain_flag_days = int(
    (
        (
            filtered_daily["knee_pain_0_10"]
            >= 6
        )
        |
        (
            filtered_daily["ankle_pain_0_10"]
            >= 6
        )
    ).sum()
)


# ============================================================
# KPI CARDS
# ============================================================

kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4 = (
    st.columns(4)
)

with kpi_col_1:
    st.metric(
        "Current Readiness",
        f"{latest['readiness_score']:.1f}/100",
        delta=(
            f"{readiness_delta:+.1f}"
            if readiness_delta is not None
            else None
        ),
    )

with kpi_col_2:
    st.metric(
        "Average Sleep",
        f"{average_sleep:.1f} hrs",
    )

with kpi_col_3:
    st.metric(
        "Average Soreness",
        f"{average_soreness:.1f}/10",
        delta_color="inverse",
    )

with kpi_col_4:
    st.metric(
        "Low Readiness Days",
        f"{low_readiness_days}",
        delta=f"{pain_flag_days} pain-flag days",
        delta_color="inverse",
    )


# ============================================================
# LATEST RECOMMENDATION
# ============================================================

recommendation = latest["recommendation"]
reason = latest["recommendation_reason"]
action = build_recovery_action(
    recommendation
)

recommendation_html = f"""
<div class="recovery-card">
    <div class="recovery-title">
        Latest Recommendation: {recommendation}
    </div>

    <div class="recovery-text">
        <strong>Reason:</strong> {reason}<br>
        <strong>Suggested action:</strong> {action}<br><br>

        <strong>Current inputs:</strong>
        Sleep {latest['sleep_hours']:.1f} hours,
        soreness {latest['soreness_overall_1_10']:.0f}/10,
        energy {latest['energy_1_5']:.0f}/5,
        knee pain {latest['knee_pain_0_10']:.0f}/10,
        ankle pain {latest['ankle_pain_0_10']:.0f}/10.
    </div>
</div>
"""

st.html(recommendation_html)


# ============================================================
# READINESS TREND
# ============================================================

st.subheader("Readiness Trend")

readiness_figure = go.Figure()

readiness_figure.add_trace(
    go.Scatter(
        x=filtered_daily["log_date"],
        y=filtered_daily["readiness_score"],
        mode="lines+markers",
        name="Readiness score",
        customdata=filtered_daily[
            [
                "sleep_hours",
                "soreness_overall_1_10",
                "energy_1_5",
                "seven_day_training_load",
            ]
        ],
        hovertemplate=(
            "Date: %{x|%b %d, %Y}"
            "<br>Readiness: %{y:.1f}"
            "<br>Sleep: %{customdata[0]:.1f} hrs"
            "<br>Soreness: %{customdata[1]:.0f}/10"
            "<br>Energy: %{customdata[2]:.0f}/5"
            "<br>7-day load: %{customdata[3]:.0f}"
            "<extra></extra>"
        ),
    )
)

readiness_figure.add_hrect(
    y0=70,
    y1=100,
    opacity=0.08,
    line_width=0,
    annotation_text="Train Hard",
)

readiness_figure.add_hrect(
    y0=50,
    y1=70,
    opacity=0.08,
    line_width=0,
    annotation_text="Modify Training",
)

readiness_figure.add_hrect(
    y0=0,
    y1=50,
    opacity=0.08,
    line_width=0,
    annotation_text="Prioritize Recovery",
)

readiness_figure.update_layout(
    height=450,
    xaxis_title="Date",
    yaxis_title="Readiness Score",
    yaxis_range=[0, 100],
    showlegend=False,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    readiness_figure,
    width="stretch",
)


# ============================================================
# READINESS COMPONENTS
# ============================================================

st.subheader("Latest Readiness Components")

component_data = pd.DataFrame(
    {
        "Component": [
            "Sleep duration",
            "Sleep quality",
            "Energy",
            "Motivation",
            "Low stress",
            "Low soreness",
        ],
        "Score": [
            min(
                latest["sleep_hours"] / 9,
                1,
            ) * 100,
            (
                latest["sleep_quality_1_5"]
                - 1
            ) / 4 * 100,
            (
                latest["energy_1_5"]
                - 1
            ) / 4 * 100,
            (
                latest["motivation_1_5"]
                - 1
            ) / 4 * 100,
            (
                5
                - latest["stress_1_5"]
            ) / 4 * 100,
            (
                10
                - latest[
                    "soreness_overall_1_10"
                ]
            ) / 9 * 100,
        ],
    }
)

component_figure = px.bar(
    component_data,
    x="Score",
    y="Component",
    orientation="h",
    range_x=[0, 100],
)

component_figure.update_layout(
    height=390,
    showlegend=False,
    xaxis_title="Component Score",
    yaxis_title=None,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    component_figure,
    width="stretch",
)


# ============================================================
# SLEEP AND PERFORMANCE
# ============================================================

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Previous-Night Sleep vs Performance")

    sleep_performance = filtered_performance.dropna(
        subset=[
            "previous_night_sleep_hours",
            "metric_value",
        ]
    ).copy()

    sleep_corr, sleep_sample = safe_correlation(
        sleep_performance,
        "previous_night_sleep_hours",
        "metric_value",
    )

    if sleep_performance.empty:
        st.info(
            "No matched sleep and performance records are "
            "available."
        )
    else:
        sleep_figure = px.scatter(
            sleep_performance,
            x="previous_night_sleep_hours",
            y="metric_value",
            trendline=(
                "ols"
                if len(sleep_performance) >= 3
                else None
            ),
            hover_data={
                "test_date": True,
                "readiness_score": ":.1f",
                "soreness_overall_1_10": ":.0f",
            },
            labels={
                "previous_night_sleep_hours": (
                    "Previous-Night Sleep (hours)"
                ),
                "metric_value": (
                    selected_metric
                    .replace("_", " ")
                    .title()
                ),
            },
        )

        sleep_figure.update_layout(
            height=420,
            showlegend=False,
            margin={
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
        )

        st.plotly_chart(
            sleep_figure,
            width="stretch",
        )

        st.caption(
            f"Correlation: "
            f"{sleep_corr:.2f}"
            if sleep_corr is not None
            else "Correlation unavailable"
        )

        st.caption(
            f"Relationship: "
            f"{correlation_label(sleep_corr)}; "
            f"sample size: {sleep_sample} tests."
        )

with right_col:
    st.subheader("Soreness vs Performance")

    soreness_performance = (
        filtered_performance.dropna(
            subset=[
                "soreness_overall_1_10",
                "metric_value",
            ]
        )
        .copy()
    )

    soreness_performance[
        "soreness_group"
    ] = create_soreness_group(
        soreness_performance[
            "soreness_overall_1_10"
        ]
    )

    soreness_corr, soreness_sample = safe_correlation(
        soreness_performance,
        "soreness_overall_1_10",
        "metric_value",
    )

    if soreness_performance.empty:
        st.info(
            "No matched soreness and performance records are "
            "available."
        )
    else:
        soreness_figure = px.box(
            soreness_performance,
            x="soreness_group",
            y="metric_value",
            points="all",
            labels={
                "soreness_group": "Soreness Level",
                "metric_value": (
                    selected_metric
                    .replace("_", " ")
                    .title()
                ),
            },
        )

        soreness_figure.update_layout(
            height=420,
            showlegend=False,
            margin={
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
        )

        st.plotly_chart(
            soreness_figure,
            width="stretch",
        )

        st.caption(
            (
                f"Correlation: {soreness_corr:.2f}; "
                f"relationship: "
                f"{correlation_label(soreness_corr)}; "
                f"sample size: {soreness_sample} tests."
            )
            if soreness_corr is not None
            else (
                "There are not enough matched records to "
                "calculate a correlation."
            )
        )


# ============================================================
# RECOVERY HEATMAP
# ============================================================

st.subheader("Recovery Calendar")

heatmap_data = filtered_daily.copy()

heatmap_data["week"] = (
    heatmap_data["log_date"]
    .dt.to_period("W")
    .apply(lambda period: period.start_time)
)

heatmap_data["weekday"] = (
    heatmap_data["log_date"]
    .dt.day_name()
)

weekday_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

heatmap_table = heatmap_data.pivot_table(
    index="weekday",
    columns="week",
    values="readiness_score",
    aggfunc="mean",
).reindex(weekday_order)

heatmap_figure = go.Figure(
    data=go.Heatmap(
        z=heatmap_table.values,
        x=heatmap_table.columns,
        y=heatmap_table.index,
        colorbar={
            "title": "Readiness",
        },
        zmin=0,
        zmax=100,
        hovertemplate=(
            "Week: %{x|%b %d, %Y}"
            "<br>Day: %{y}"
            "<br>Readiness: %{z:.1f}"
            "<extra></extra>"
        ),
    )
)

heatmap_figure.update_layout(
    height=420,
    xaxis_title="Week Beginning",
    yaxis_title=None,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    heatmap_figure,
    width="stretch",
)


# ============================================================
# LOAD AND RECOVERY RELATIONSHIP
# ============================================================

st.subheader("Training Load and Readiness")

load_recovery_figure = go.Figure()

load_recovery_figure.add_trace(
    go.Bar(
        x=filtered_daily["log_date"],
        y=filtered_daily[
            "seven_day_training_load"
        ],
        name="7-day training load",
    )
)

load_recovery_figure.add_trace(
    go.Scatter(
        x=filtered_daily["log_date"],
        y=filtered_daily["readiness_score"],
        mode="lines+markers",
        name="Readiness",
        yaxis="y2",
    )
)

load_recovery_figure.update_layout(
    height=440,
    xaxis_title="Date",
    yaxis={
        "title": "7-Day Training Load",
    },
    yaxis2={
        "title": "Readiness Score",
        "overlaying": "y",
        "side": "right",
        "range": [0, 100],
    },
    legend_title=None,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    load_recovery_figure,
    width="stretch",
)


# ============================================================
# RECOVERY SUMMARY
# ============================================================

if sleep_corr is None:
    sleep_summary = (
        "There are not enough matched tests to evaluate the "
        "sleep-performance relationship."
    )
elif sleep_corr >= 0.30:
    sleep_summary = (
        "More sleep is associated with stronger performance in "
        "the selected sample."
    )
elif sleep_corr <= -0.30:
    sleep_summary = (
        "The sample shows a negative sleep-performance "
        "association. Review testing timing and other confounding "
        "factors before interpreting this result."
    )
else:
    sleep_summary = (
        "Sleep has a weak relationship with performance in the "
        "current sample."
    )

if soreness_corr is None:
    soreness_summary = (
        "There are not enough matched tests to evaluate soreness."
    )
elif soreness_corr <= -0.30:
    soreness_summary = (
        "Higher soreness is associated with lower performance."
    )
elif soreness_corr >= 0.30:
    soreness_summary = (
        "Higher soreness is associated with higher performance "
        "in this sample, which may reflect training timing or a "
        "small sample rather than a useful causal relationship."
    )
else:
    soreness_summary = (
        "Soreness has a weak relationship with performance in "
        "the current sample."
    )

summary_html = f"""
<div class="recovery-card">
    <div class="recovery-title">Recovery Summary</div>

    <div class="recovery-text">
        <strong>Sleep:</strong> {sleep_summary}<br><br>

        <strong>Soreness:</strong> {soreness_summary}<br><br>

        <strong>Current decision:</strong>
        {recommendation}. {action}<br><br>

        Correlations describe associations only. They do not prove
        that sleep, soreness, or training load directly caused a
        performance result.
    </div>
</div>
"""

st.html(summary_html)


# ============================================================
# DATA TABLE
# ============================================================

with st.expander("View recovery records"):
    display_columns = [
        "log_date",
        "sleep_hours",
        "sleep_quality_1_5",
        "soreness_overall_1_10",
        "knee_pain_0_10",
        "ankle_pain_0_10",
        "energy_1_5",
        "stress_1_5",
        "motivation_1_5",
        "readiness_score",
        "daily_training_load",
        "seven_day_training_load",
        "load_spike_ratio",
        "recommendation",
        "recommendation_reason",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in filtered_daily.columns
    ]

    st.dataframe(
        filtered_daily[
            available_columns
        ].sort_values(
            "log_date",
            ascending=False,
        ),
        width="stretch",
        hide_index=True,
    )