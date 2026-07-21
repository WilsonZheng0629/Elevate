from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Elevate | Performance",
    page_icon="📈",
    layout="wide",
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PERFORMANCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "performance_features.csv"
)

BLOCKS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "training_blocks.csv"
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not PERFORMANCE_PATH.exists():
        raise FileNotFoundError(
            "performance_features.csv was not found. "
            "Run python src/etl_pipeline.py first."
        )

    performance = pd.read_csv(
        PERFORMANCE_PATH,
        parse_dates=["test_date", "previous_session_date"],
    )

    if BLOCKS_PATH.exists():
        blocks = pd.read_csv(
            BLOCKS_PATH,
            parse_dates=["start_date", "end_date"],
        )
    else:
        blocks = pd.DataFrame()

    return performance, blocks


def metric_label(metric_name: str) -> str:
    labels = {
        "approach_vertical": "Approach Vertical",
        "standing_vertical": "Standing Vertical",
        "approach_touch": "Approach Touch",
        "standing_touch": "Standing Touch",
    }

    return labels.get(
        metric_name,
        metric_name.replace("_", " ").title(),
    )


def calculate_recent_change(
    metric_data: pd.DataFrame,
) -> tuple[float | None, float | None, float | None]:
    """
    Compare the latest three-test average with the previous
    three-test average.
    """

    if metric_data.empty:
        return None, None, None

    values = (
        metric_data
        .sort_values("test_date")["metric_value"]
        .dropna()
    )

    if len(values) < 3:
        return float(values.mean()), None, None

    recent_average = float(values.tail(3).mean())

    if len(values) < 6:
        return recent_average, None, None

    previous_average = float(
        values.iloc[-6:-3].mean()
    )

    change = recent_average - previous_average

    return recent_average, previous_average, change


try:
    performance, training_blocks = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()


st.title("Performance Trends")

st.caption(
    "Track vertical-jump progress, consistency, personal bests, "
    "and changes across training blocks."
)

# SIDEBAR FILTERS

athlete_ids = sorted(
    performance["athlete_id"]
    .dropna()
    .unique()
    .tolist()
)

selected_athlete = st.sidebar.selectbox(
    "Athlete",
    athlete_ids,
)

athlete_data = performance.loc[
    performance["athlete_id"] == selected_athlete
].copy()

metric_options = (
    athlete_data["metric_name"]
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
    metric_options,
    index=metric_options.index(default_metric),
    format_func=metric_label,
)

metric_data = (
    athlete_data.loc[
        athlete_data["metric_name"] == selected_metric
    ]
    .copy()
    .sort_values("test_date")
)

if metric_data.empty:
    st.warning("No data exists for the selected metric.")
    st.stop()

minimum_date = metric_data["test_date"].min().date()
maximum_date = metric_data["test_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

if (
    isinstance(selected_dates, tuple)
    and len(selected_dates) == 2
):
    start_date, end_date = selected_dates
else:
    start_date, end_date = minimum_date, maximum_date

metric_data = metric_data.loc[
    metric_data["test_date"]
    .dt.date
    .between(start_date, end_date)
].copy()

block_options = ["All blocks"]

if "block_id" in metric_data.columns:
    block_ids = (
        metric_data["block_id"]
        .dropna()
        .unique()
        .tolist()
    )

    block_options.extend(
        sorted(block_ids)
    )

selected_block = st.sidebar.selectbox(
    "Training block",
    block_options,
)

if selected_block != "All blocks":
    metric_data = metric_data.loc[
        metric_data["block_id"] == selected_block
    ].copy()

if metric_data.empty:
    st.warning(
        "No test records match the selected filters."
    )
    st.stop()


# KPI CALCULATIONS

latest_result = float(
    metric_data.iloc[-1]["metric_value"]
)

personal_best = float(
    metric_data["metric_value"].max()
)

baseline = float(
    metric_data.iloc[0]["metric_value"]
)

absolute_improvement = latest_result - baseline

percentage_improvement = (
    absolute_improvement
    / baseline
    * 100
    if baseline != 0
    else None
)

recent_average, previous_average, recent_change = (
    calculate_recent_change(metric_data)
)

standard_deviation = float(
    metric_data["metric_value"].std()
) if len(metric_data) > 1 else 0.0

coefficient_of_variation = (
    standard_deviation
    / metric_data["metric_value"].mean()
    * 100
    if metric_data["metric_value"].mean() != 0
    else None
)


# KPI CARDS

col_1, col_2, col_3, col_4 = st.columns(4)

with col_1:
    st.metric(
        "Latest Result",
        f"{latest_result:.1f} in",
        delta=f"{absolute_improvement:+.1f} from baseline",
    )

with col_2:
    st.metric(
        "Personal Best",
        f"{personal_best:.1f} in",
    )

with col_3:
    st.metric(
        "Recent 3-Test Average",
        f"{recent_average:.1f} in",
        delta=(
            f"{recent_change:+.1f}"
            if recent_change is not None
            else None
        ),
    )

with col_4:
    st.metric(
        "Consistency",
        (
            f"{coefficient_of_variation:.1f}% CV"
            if coefficient_of_variation is not None
            else "Not available"
        ),
        help=(
            "A lower coefficient of variation means test "
            "results are more consistent."
        ),
    )



# MAIN TREND CHART


st.subheader(f"{metric_label(selected_metric)} Trend")

trend_figure = go.Figure()

trend_figure.add_trace(
    go.Scatter(
        x=metric_data["test_date"],
        y=metric_data["metric_value"],
        mode="lines+markers",
        name="Test result",
        customdata=metric_data[
            [
                "change_from_previous_test",
                "change_from_baseline",
            ]
        ],
        hovertemplate=(
            "Date: %{x|%b %d, %Y}"
            "<br>Result: %{y:.1f} in"
            "<br>Change from previous: %{customdata[0]:+.1f}"
            "<br>Change from baseline: %{customdata[1]:+.1f}"
            "<extra></extra>"
        ),
    )
)

trend_figure.add_trace(
    go.Scatter(
        x=metric_data["test_date"],
        y=metric_data["three_test_rolling_average"],
        mode="lines",
        name="3-test rolling average",
        line={"dash": "dash"},
    )
)

personal_best_rows = metric_data.loc[
    metric_data["metric_value"] == personal_best
]

trend_figure.add_trace(
    go.Scatter(
        x=personal_best_rows["test_date"],
        y=personal_best_rows["metric_value"],
        mode="markers",
        name="Personal best",
        marker={
            "size": 13,
            "symbol": "star",
        },
    )
)


# Add training-block shading when block data is available.
if not training_blocks.empty:
    athlete_blocks = training_blocks.loc[
        training_blocks["athlete_id"] == selected_athlete
    ].copy()

    for _, block in athlete_blocks.iterrows():
        trend_figure.add_vrect(
            x0=block["start_date"],
            x1=block["end_date"],
            opacity=0.08,
            line_width=0,
            annotation_text=block["block_name"],
            annotation_position="top left",
        )


trend_figure.update_layout(
    height=500,
    xaxis_title="Test Date",
    yaxis_title="Height (inches)",
    hovermode="x unified",
    legend_title=None,
    margin={
        "l": 20,
        "r": 20,
        "t": 30,
        "b": 20,
    },
)

st.plotly_chart(
    trend_figure,
    width="stretch",
)



# PROGRESS AND CONSISTENCY

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Change From Baseline")

    baseline_chart = px.bar(
        metric_data,
        x="test_date",
        y="change_from_baseline",
        labels={
            "test_date": "Test Date",
            "change_from_baseline": (
                "Change From Baseline (in)"
            ),
        },
    )

    baseline_chart.add_hline(
        y=0,
        line_dash="dash",
    )

    baseline_chart.update_layout(
        height=390,
        showlegend=False,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        baseline_chart,
        width="stretch",
    )

with right_col:
    st.subheader("Test-to-Test Change")

    change_chart = px.bar(
        metric_data,
        x="test_date",
        y="change_from_previous_test",
        labels={
            "test_date": "Test Date",
            "change_from_previous_test": (
                "Change From Previous Test (in)"
            ),
        },
    )

    change_chart.add_hline(
        y=0,
        line_dash="dash",
    )

    change_chart.update_layout(
        height=390,
        showlegend=False,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        change_chart,
        width="stretch",
    )



# PERFORMANCE DISTRIBUTION


left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Performance Distribution")

    distribution_chart = px.histogram(
        metric_data,
        x="metric_value",
        nbins=min(12, len(metric_data)),
        labels={
            "metric_value": "Jump Height (in)",
            "count": "Number of Tests",
        },
    )

    distribution_chart.update_layout(
        height=380,
        showlegend=False,
    )

    st.plotly_chart(
        distribution_chart,
        width="stretch",
    )

with right_col:
    st.subheader("Testing Consistency")

    consistency_table = pd.DataFrame(
    {
        "Metric": [
            "Test count",
            "Mean",
            "Median",
            "Standard deviation",
            "Coefficient of variation",
            "Minimum",
            "Maximum",
        ],
        "Value": [
            str(len(metric_data)),
            f"{metric_data['metric_value'].mean():.2f} in",
            f"{metric_data['metric_value'].median():.2f} in",
            f"{standard_deviation:.2f} in",
            (
                f"{coefficient_of_variation:.2f}%"
                if coefficient_of_variation is not None
                else "N/A"
            ),
            f"{metric_data['metric_value'].min():.2f} in",
            f"{metric_data['metric_value'].max():.2f} in",
        ],
    }
)

    st.dataframe(
        consistency_table,
        width="stretch",
        hide_index=True,
    )



# AUTOMATED INTERPRETATION


st.subheader("Performance Summary")

if recent_change is None:
    trend_message = (
        "There are not yet enough tests to compare two "
        "three-test periods."
    )
elif recent_change > 0.5:
    trend_message = (
        f"Recent performance is improving. The latest three-test "
        f"average is {recent_change:.1f} inches higher than the "
        "previous three-test average."
    )
elif recent_change < -0.5:
    trend_message = (
        f"Recent performance has declined. The latest three-test "
        f"average is {abs(recent_change):.1f} inches lower than "
        "the previous three-test average."
    )
else:
    trend_message = (
        "Recent performance is relatively stable, with less than "
        "a 0.5-inch difference between the latest two three-test "
        "periods."
    )

if coefficient_of_variation is None:
    consistency_message = (
        "More test results are needed to evaluate consistency."
    )
elif coefficient_of_variation <= 5:
    consistency_message = (
        "Testing results are highly consistent."
    )
elif coefficient_of_variation <= 10:
    consistency_message = (
        "Testing consistency is moderate."
    )
else:
    consistency_message = (
        "Testing results are relatively variable. Standardizing "
        "warm-up, surface, measurement method, and fatigue may "
        "improve interpretation."
    )

st.info(
    f"""
    **Trend:** {trend_message}

    **Overall improvement:** The latest result is
    `{absolute_improvement:+.1f} inches`
    ({percentage_improvement:+.1f}%) relative to the first
    filtered test.

    **Consistency:** {consistency_message}

    These results describe observed trends and do not prove that
    any specific workout caused the performance change.
    """
)


# RAW TEST DATA

with st.expander("View performance-test records"):
    display_columns = [
        "test_date",
        "metric_name",
        "metric_value",
        "three_test_rolling_average",
        "change_from_previous_test",
        "change_from_baseline",
        "percent_change_from_baseline",
        "personal_best_flag",
        "warmup_quality_1_5",
        "surface",
        "shoes",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in metric_data.columns
    ]

    st.dataframe(
        metric_data[available_columns],
        width="stretch",
        hide_index=True,
    )