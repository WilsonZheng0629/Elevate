from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Elevate | Training Blocks",
    page_icon="📊",
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

TRAINING_BLOCKS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "training_blocks.csv"
)

TRAINING_SESSIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "training_sessions.csv"
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

        .analysis-card {
            border-radius: 14px;
            padding: 18px;
            margin-top: 8px;
            margin-bottom: 16px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background-color: rgba(255, 255, 255, 0.04);
        }

        .analysis-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .analysis-text {
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
    pd.DataFrame,
    pd.DataFrame,
]:
    required_files = [
        DAILY_FEATURES_PATH,
        PERFORMANCE_FEATURES_PATH,
        TRAINING_BLOCKS_PATH,
        TRAINING_SESSIONS_PATH,
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
            "Required files were not found:\n"
            f"{missing_text}\n\n"
            "Run the database and ETL scripts first."
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

    blocks = pd.read_csv(
        TRAINING_BLOCKS_PATH,
        parse_dates=[
            "start_date",
            "end_date",
        ],
    )

    sessions = pd.read_csv(
        TRAINING_SESSIONS_PATH,
        parse_dates=["session_date"],
    )

    return daily, performance, blocks, sessions


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_metric_name(metric_name: str) -> str:
    return (
        str(metric_name)
        .replace("_", " ")
        .title()
    )


def safe_percent_change(
    starting_value: float,
    ending_value: float,
) -> float | None:
    if pd.isna(starting_value) or pd.isna(ending_value):
        return None

    if starting_value == 0:
        return None

    return (
        ending_value
        - starting_value
    ) / starting_value * 100


def build_block_summary(
    athlete_id: int,
    metric_name: str,
    blocks: pd.DataFrame,
    sessions: pd.DataFrame,
    performance: pd.DataFrame,
    daily: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one analytical row per training block.

    Training, performance, and recovery are aggregated
    separately before being combined.
    """

    athlete_blocks = (
        blocks.loc[
            blocks["athlete_id"] == athlete_id
        ]
        .copy()
        .sort_values("start_date")
    )

    summary_rows: list[dict[str, object]] = []

    for _, block in athlete_blocks.iterrows():
        block_id = block["block_id"]
        start_date = block["start_date"]
        end_date = block["end_date"]

        block_sessions = sessions.loc[
            (
                sessions["athlete_id"]
                == athlete_id
            )
            &
            (
                sessions["block_id"]
                == block_id
            )
            &
            (
                sessions["completed"]
                == 1
            )
            &
            (
                sessions["session_type"]
                .astype(str)
                .str.lower()
                != "rest"
            )
        ].copy()

        block_tests = performance.loc[
            (
                performance["athlete_id"]
                == athlete_id
            )
            &
            (
                performance["block_id"]
                == block_id
            )
            &
            (
                performance["metric_name"]
                == metric_name
            )
        ].copy().sort_values(
            [
                "test_date",
                "test_id",
            ]
        )

        block_daily = daily.loc[
            (
                daily["athlete_id"]
                == athlete_id
            )
            &
            (
                daily["log_date"]
                .between(
                    start_date,
                    end_date,
                )
            )
        ].copy()

        starting_performance = (
            float(
                block_tests.iloc[0][
                    "metric_value"
                ]
            )
            if not block_tests.empty
            else np.nan
        )

        ending_performance = (
            float(
                block_tests.iloc[-1][
                    "metric_value"
                ]
            )
            if not block_tests.empty
            else np.nan
        )

        best_performance = (
            float(
                block_tests[
                    "metric_value"
                ].max()
            )
            if not block_tests.empty
            else np.nan
        )

        absolute_improvement = (
            ending_performance
            - starting_performance
            if (
                not pd.isna(
                    starting_performance
                )
                and not pd.isna(
                    ending_performance
                )
            )
            else np.nan
        )

        percentage_improvement = (
            safe_percent_change(
                starting_performance,
                ending_performance,
            )
        )

        completed_sessions = len(
            block_sessions
        )

        total_training_load = float(
            block_sessions[
                "session_load"
            ].sum()
        )

        total_training_minutes = float(
            block_sessions[
                "duration_minutes"
            ].sum()
        )

        average_rpe = (
            float(
                block_sessions[
                    "intensity_rpe"
                ].mean()
            )
            if not block_sessions.empty
            else np.nan
        )

        block_days = (
            end_date - start_date
        ).days + 1

        block_weeks = max(
            block_days / 7,
            0,
        )

        planned_frequency = block.get(
            "planned_frequency_per_week",
            np.nan,
        )

        expected_sessions = (
            planned_frequency
            * block_weeks
            if not pd.isna(
                planned_frequency
            )
            else np.nan
        )

        adherence_percent = (
            completed_sessions
            / expected_sessions
            * 100
            if (
                not pd.isna(
                    expected_sessions
                )
                and expected_sessions > 0
            )
            else np.nan
        )

        average_readiness = (
            float(
                block_daily[
                    "readiness_score"
                ].mean()
            )
            if not block_daily.empty
            else np.nan
        )

        average_sleep = (
            float(
                block_daily[
                    "sleep_hours"
                ].mean()
            )
            if not block_daily.empty
            else np.nan
        )

        average_soreness = (
            float(
                block_daily[
                    "soreness_overall_1_10"
                ].mean()
            )
            if not block_daily.empty
            else np.nan
        )

        improvement_per_1000_load = (
            absolute_improvement
            / total_training_load
            * 1000
            if (
                not pd.isna(
                    absolute_improvement
                )
                and total_training_load > 0
            )
            else np.nan
        )

        summary_rows.append(
            {
                "block_id": block_id,
                "block_name": block[
                    "block_name"
                ],
                "start_date": start_date,
                "end_date": end_date,
                "block_focus": block.get(
                    "block_focus",
                    None,
                ),
                "planned_frequency_per_week": (
                    planned_frequency
                ),
                "block_weeks": block_weeks,
                "test_count": len(
                    block_tests
                ),
                "starting_performance": (
                    starting_performance
                ),
                "ending_performance": (
                    ending_performance
                ),
                "best_performance": (
                    best_performance
                ),
                "absolute_improvement": (
                    absolute_improvement
                ),
                "percentage_improvement": (
                    percentage_improvement
                ),
                "completed_sessions": (
                    completed_sessions
                ),
                "expected_sessions": (
                    expected_sessions
                ),
                "adherence_percent": (
                    adherence_percent
                ),
                "total_training_load": (
                    total_training_load
                ),
                "total_training_minutes": (
                    total_training_minutes
                ),
                "average_rpe": (
                    average_rpe
                ),
                "average_readiness": (
                    average_readiness
                ),
                "average_sleep": (
                    average_sleep
                ),
                "average_soreness": (
                    average_soreness
                ),
                "improvement_per_1000_load": (
                    improvement_per_1000_load
                ),
            }
        )

    summary = pd.DataFrame(
        summary_rows
    )

    numeric_columns = [
        "block_weeks",
        "starting_performance",
        "ending_performance",
        "best_performance",
        "absolute_improvement",
        "percentage_improvement",
        "expected_sessions",
        "adherence_percent",
        "total_training_load",
        "total_training_minutes",
        "average_rpe",
        "average_readiness",
        "average_sleep",
        "average_soreness",
        "improvement_per_1000_load",
    ]

    for column in numeric_columns:
        if column in summary.columns:
            summary[column] = (
                pd.to_numeric(
                    summary[column],
                    errors="coerce",
                )
            )

    return summary


def calculate_correlation_matrix(
    performance: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate correlations using matched performance records.
    """

    candidate_columns = [
        "metric_value",
        "previous_night_sleep_hours",
        "sleep_quality_1_5",
        "soreness_overall_1_10",
        "energy_1_5",
        "stress_1_5",
        "motivation_1_5",
        "readiness_score",
        "seven_day_training_load",
        "previous_session_load",
        "days_since_previous_session",
    ]

    available_columns = [
        column
        for column in candidate_columns
        if column in performance.columns
    ]

    if len(available_columns) < 2:
        return pd.DataFrame()

    numeric_data = performance[
        available_columns
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    return numeric_data.corr()


def run_regression(
    performance: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    dict[str, float | int | str],
]:
    """
    Run a simple interpretable OLS regression.

    Outcome:
    - Performance metric value

    Predictors:
    - Previous-night sleep
    - Soreness
    - Seven-day load
    - Readiness
    """

    predictor_columns = [
        "previous_night_sleep_hours",
        "soreness_overall_1_10",
        "seven_day_training_load",
        "readiness_score",
    ]

    required_columns = [
        "metric_value",
        *predictor_columns,
    ]

    if not set(
        required_columns
    ).issubset(
        performance.columns
    ):
        return (
            pd.DataFrame(),
            {
                "status": (
                    "Required regression "
                    "columns are missing."
                )
            },
        )

    model_data = (
        performance[
            required_columns
        ]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .dropna()
    )

    if len(model_data) < 10:
        return (
            pd.DataFrame(),
            {
                "status": (
                    "At least 10 complete "
                    "performance records are "
                    "required."
                ),
                "sample_size": len(
                    model_data
                ),
            },
        )

    y = model_data[
        "metric_value"
    ]

    x = model_data[
        predictor_columns
    ]

    x = sm.add_constant(
        x,
        has_constant="add",
    )

    try:
        model = sm.OLS(
            y,
            x,
        ).fit()
    except Exception as error:
        return (
            pd.DataFrame(),
            {
                "status": (
                    "Regression could not be "
                    f"estimated: {error}"
                )
            },
        )

    confidence_intervals = (
        model.conf_int()
    )

    coefficients = pd.DataFrame(
        {
            "variable": model.params.index,
            "coefficient": (
                model.params.values
            ),
            "standard_error": (
                model.bse.values
            ),
            "p_value": (
                model.pvalues.values
            ),
            "confidence_interval_low": (
                confidence_intervals[
                    0
                ].values
            ),
            "confidence_interval_high": (
                confidence_intervals[
                    1
                ].values
            ),
        }
    )

    coefficients = coefficients.round(
        {
            "coefficient": 4,
            "standard_error": 4,
            "p_value": 4,
            "confidence_interval_low": 4,
            "confidence_interval_high": 4,
        }
    )

    model_summary = {
        "status": "Success",
        "sample_size": int(
            model.nobs
        ),
        "r_squared": float(
            model.rsquared
        ),
        "adjusted_r_squared": float(
            model.rsquared_adj
        ),
        "f_statistic": (
            float(model.fvalue)
            if model.fvalue is not None
            else np.nan
        ),
        "model_p_value": (
            float(model.f_pvalue)
            if model.f_pvalue is not None
            else np.nan
        ),
    }

    return (
        coefficients,
        model_summary,
    )


# ============================================================
# LOAD DATA
# ============================================================

try:
    (
        daily_features,
        performance_features,
        training_blocks,
        training_sessions,
    ) = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()


# ============================================================
# PAGE HEADER
# ============================================================

st.title("Training Block Review")

st.caption(
    "Compare training phases by performance gain, workload, "
    "adherence, recovery, and statistical relationships."
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================

athlete_ids = sorted(
    training_blocks[
        "athlete_id"
    ]
    .dropna()
    .unique()
    .tolist()
)

selected_athlete = st.sidebar.selectbox(
    "Athlete",
    options=athlete_ids,
)

athlete_performance = (
    performance_features.loc[
        performance_features[
            "athlete_id"
        ]
        == selected_athlete
    ]
    .copy()
)

metric_options = (
    athlete_performance[
        "metric_name"
    ]
    .dropna()
    .sort_values()
    .unique()
    .tolist()
)

default_metric = (
    "approach_vertical"
    if "approach_vertical"
    in metric_options
    else metric_options[0]
)

selected_metric = st.sidebar.selectbox(
    "Performance metric",
    options=metric_options,
    index=metric_options.index(
        default_metric
    ),
    format_func=format_metric_name,
)

minimum_tests = st.sidebar.slider(
    "Minimum tests per block",
    min_value=1,
    max_value=10,
    value=2,
    help=(
        "Blocks with fewer than this number "
        "of tests are excluded from ranking."
    ),
)


# ============================================================
# BUILD BLOCK SUMMARY
# ============================================================

block_summary = build_block_summary(
    athlete_id=selected_athlete,
    metric_name=selected_metric,
    blocks=training_blocks,
    sessions=training_sessions,
    performance=performance_features,
    daily=daily_features,
)

if block_summary.empty:
    st.warning(
        "No training block data is available."
    )
    st.stop()

eligible_blocks = block_summary.loc[
    block_summary["test_count"]
    >= minimum_tests
].copy()

if eligible_blocks.empty:
    st.warning(
        "No blocks meet the selected minimum "
        "test requirement."
    )
    st.stop()


# ============================================================
# KPI CALCULATIONS
# ============================================================

rankable_improvement = (
    eligible_blocks.dropna(
        subset=[
            "absolute_improvement"
        ]
    )
)

rankable_efficiency = (
    eligible_blocks.dropna(
        subset=[
            "improvement_per_1000_load"
        ]
    )
)

rankable_adherence = (
    eligible_blocks.dropna(
        subset=[
            "adherence_percent"
        ]
    )
)

best_gain_block = (
    rankable_improvement.sort_values(
        "absolute_improvement",
        ascending=False,
    ).iloc[0]
    if not rankable_improvement.empty
    else None
)

best_efficiency_block = (
    rankable_efficiency.sort_values(
        "improvement_per_1000_load",
        ascending=False,
    ).iloc[0]
    if not rankable_efficiency.empty
    else None
)

best_adherence_block = (
    rankable_adherence.sort_values(
        "adherence_percent",
        ascending=False,
    ).iloc[0]
    if not rankable_adherence.empty
    else None
)

total_load = float(
    eligible_blocks[
        "total_training_load"
    ].sum()
)


# ============================================================
# KPI CARDS
# ============================================================

kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4 = (
    st.columns(4)
)

with kpi_col_1:
    st.metric(
        "Blocks Analyzed",
        f"{len(eligible_blocks)}",
    )

with kpi_col_2:
    if best_gain_block is not None:
        st.metric(
            "Largest Performance Gain",
            (
                f"{best_gain_block['absolute_improvement']:+.2f} in"
            ),
            delta=best_gain_block[
                "block_name"
            ],
        )
    else:
        st.metric(
            "Largest Performance Gain",
            "No data",
        )

with kpi_col_3:
    if best_efficiency_block is not None:
        st.metric(
            "Best Block Efficiency",
            (
                f"{best_efficiency_block['improvement_per_1000_load']:+.3f}"
            ),
            delta=best_efficiency_block[
                "block_name"
            ],
            help=(
                "Performance improvement per "
                "1,000 training-load units."
            ),
        )
    else:
        st.metric(
            "Best Block Efficiency",
            "No data",
        )

with kpi_col_4:
    st.metric(
        "Total Training Load",
        f"{total_load:,.0f}",
    )


# ============================================================
# STARTING VS ENDING PERFORMANCE
# ============================================================

st.subheader(
    "Starting vs Ending Performance"
)

comparison_data = (
    eligible_blocks[
        [
            "block_name",
            "starting_performance",
            "ending_performance",
        ]
    ]
    .melt(
        id_vars="block_name",
        value_vars=[
            "starting_performance",
            "ending_performance",
        ],
        var_name="measurement",
        value_name="performance",
    )
)

comparison_data[
    "measurement"
] = comparison_data[
    "measurement"
].map(
    {
        "starting_performance": (
            "Starting Performance"
        ),
        "ending_performance": (
            "Ending Performance"
        ),
    }
)

comparison_figure = px.bar(
    comparison_data,
    x="block_name",
    y="performance",
    color="measurement",
    barmode="group",
    labels={
        "block_name": "Training Block",
        "performance": (
            f"{format_metric_name(selected_metric)} (in)"
        ),
        "measurement": "Measurement",
    },
)

comparison_figure.update_layout(
    height=460,
    legend_title=None,
    xaxis_tickangle=-20,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    comparison_figure,
    width="stretch",
)


# ============================================================
# IMPROVEMENT AND LOAD
# ============================================================

left_col, right_col = st.columns(2)

with left_col:
    st.subheader(
        "Block Performance Change"
    )

    improvement_figure = px.bar(
        eligible_blocks,
        x="block_name",
        y="absolute_improvement",
        hover_data={
            "starting_performance": ":.2f",
            "ending_performance": ":.2f",
            "percentage_improvement": ":.2f",
            "test_count": True,
        },
        labels={
            "block_name": "Training Block",
            "absolute_improvement": (
                "Performance Change (in)"
            ),
        },
    )

    improvement_figure.add_hline(
        y=0,
        line_dash="dash",
    )

    improvement_figure.update_layout(
        height=420,
        showlegend=False,
        xaxis_tickangle=-20,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        improvement_figure,
        width="stretch",
    )

with right_col:
    st.subheader(
        "Training Load by Block"
    )

    load_figure = px.bar(
        eligible_blocks,
        x="block_name",
        y="total_training_load",
        hover_data={
            "completed_sessions": True,
            "total_training_minutes": ":.0f",
            "average_rpe": ":.1f",
        },
        labels={
            "block_name": "Training Block",
            "total_training_load": (
                "Total Training Load"
            ),
        },
    )

    load_figure.update_layout(
        height=420,
        showlegend=False,
        xaxis_tickangle=-20,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        load_figure,
        width="stretch",
    )


# ============================================================
# BLOCK EFFICIENCY
# ============================================================

st.subheader(
    "Block Efficiency"
)

efficiency_figure = px.scatter(
    eligible_blocks,
    x="total_training_load",
    y="absolute_improvement",
    size="completed_sessions",
    text="block_name",
    hover_data={
        "percentage_improvement": ":.2f",
        "adherence_percent": ":.1f",
        "average_readiness": ":.1f",
        "average_sleep": ":.1f",
        "average_soreness": ":.1f",
    },
    labels={
        "total_training_load": (
            "Total Training Load"
        ),
        "absolute_improvement": (
            "Performance Improvement (in)"
        ),
        "completed_sessions": (
            "Completed Sessions"
        ),
    },
)

efficiency_figure.add_hline(
    y=0,
    line_dash="dash",
)

efficiency_figure.update_traces(
    textposition="top center",
)

efficiency_figure.update_layout(
    height=500,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    efficiency_figure,
    width="stretch",
)

st.caption(
    "A block in the upper-left region produced greater "
    "improvement with comparatively less training load. "
    "This does not prove that lower load caused better results."
)


# ============================================================
# ADHERENCE AND RECOVERY
# ============================================================

left_col, right_col = st.columns(2)

with left_col:
    st.subheader(
        "Training Adherence"
    )

    adherence_data = (
        eligible_blocks.dropna(
            subset=[
                "adherence_percent"
            ]
        )
    )

    if adherence_data.empty:
        st.info(
            "Adherence could not be calculated "
            "from the available block data."
        )
    else:
        adherence_figure = px.bar(
            adherence_data,
            x="block_name",
            y="adherence_percent",
            hover_data={
                "expected_sessions": ":.1f",
                "completed_sessions": True,
            },
            labels={
                "block_name": (
                    "Training Block"
                ),
                "adherence_percent": (
                    "Adherence (%)"
                ),
            },
        )

        adherence_figure.add_hline(
            y=90,
            line_dash="dash",
            annotation_text=(
                "Excellent adherence"
            ),
        )

        adherence_figure.update_layout(
            height=410,
            showlegend=False,
            xaxis_tickangle=-20,
            margin={
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
        )

        st.plotly_chart(
            adherence_figure,
            width="stretch",
        )

with right_col:
    st.subheader(
        "Average Recovery by Block"
    )

    recovery_data = (
        eligible_blocks[
            [
                "block_name",
                "average_readiness",
                "average_sleep",
                "average_soreness",
            ]
        ]
        .copy()
    )

    recovery_figure = go.Figure()

    recovery_figure.add_trace(
        go.Bar(
            x=recovery_data[
                "block_name"
            ],
            y=recovery_data[
                "average_readiness"
            ],
            name="Average readiness",
        )
    )

    recovery_figure.add_trace(
        go.Scatter(
            x=recovery_data[
                "block_name"
            ],
            y=recovery_data[
                "average_sleep"
            ],
            mode="lines+markers",
            name="Average sleep",
            yaxis="y2",
        )
    )

    recovery_figure.update_layout(
        height=410,
        xaxis_title="Training Block",
        yaxis={
            "title": "Readiness Score",
            "range": [0, 100],
        },
        yaxis2={
            "title": "Sleep Hours",
            "overlaying": "y",
            "side": "right",
        },
        legend_title=None,
        xaxis_tickangle=-20,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        recovery_figure,
        width="stretch",
    )


# ============================================================
# CORRELATION MATRIX
# ============================================================

st.subheader(
    "Performance Correlation Matrix"
)

selected_performance = (
    athlete_performance.loc[
        athlete_performance[
            "metric_name"
        ]
        == selected_metric
    ]
    .copy()
)

correlation_matrix = (
    calculate_correlation_matrix(
        selected_performance
    )
)

if correlation_matrix.empty:
    st.info(
        "There are not enough numeric fields "
        "to calculate a correlation matrix."
    )
else:
    readable_labels = {
        "metric_value": "Performance",
        "previous_night_sleep_hours": (
            "Previous-Night Sleep"
        ),
        "sleep_quality_1_5": (
            "Sleep Quality"
        ),
        "soreness_overall_1_10": (
            "Soreness"
        ),
        "energy_1_5": "Energy",
        "stress_1_5": "Stress",
        "motivation_1_5": "Motivation",
        "readiness_score": "Readiness",
        "seven_day_training_load": (
            "7-Day Load"
        ),
        "previous_session_load": (
            "Previous Session Load"
        ),
        "days_since_previous_session": (
            "Days Since Session"
        ),
    }

    correlation_display = (
        correlation_matrix.rename(
            index=readable_labels,
            columns=readable_labels,
        )
    )

    correlation_figure = px.imshow(
        correlation_display,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        aspect="auto",
        labels={
            "color": "Correlation",
        },
    )

    correlation_figure.update_layout(
        height=650,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        correlation_figure,
        width="stretch",
    )

    st.caption(
        "Correlation ranges from -1 to 1. Values near 1 show "
        "a strong positive association, values near -1 show a "
        "strong negative association, and values near 0 show "
        "little linear association."
    )


# ============================================================
# REGRESSION ANALYSIS
# ============================================================

st.subheader(
    "Exploratory Regression"
)

coefficients, model_summary = (
    run_regression(
        selected_performance
    )
)

if model_summary.get(
    "status"
) != "Success":
    st.info(
        str(
            model_summary.get(
                "status",
                "Regression unavailable.",
            )
        )
    )
else:
    regression_col_1, regression_col_2, regression_col_3 = (
        st.columns(3)
    )

    with regression_col_1:
        st.metric(
            "Regression Sample",
            f"{model_summary['sample_size']}",
        )

    with regression_col_2:
        st.metric(
            "R-Squared",
            f"{model_summary['r_squared']:.3f}",
            help=(
                "The percentage of variation "
                "in performance explained by "
                "the model predictors."
            ),
        )

    with regression_col_3:
        st.metric(
            "Adjusted R-Squared",
            (
                f"{model_summary['adjusted_r_squared']:.3f}"
            ),
        )

    variable_labels = {
        "const": "Intercept",
        "previous_night_sleep_hours": (
            "Previous-Night Sleep"
        ),
        "soreness_overall_1_10": (
            "Soreness"
        ),
        "seven_day_training_load": (
            "7-Day Training Load"
        ),
        "readiness_score": (
            "Readiness Score"
        ),
    }

    coefficients[
        "variable_label"
    ] = coefficients[
        "variable"
    ].map(
        variable_labels
    ).fillna(
        coefficients["variable"]
    )

    coefficient_figure = px.bar(
        coefficients.loc[
            coefficients["variable"]
            != "const"
        ],
        x="variable_label",
        y="coefficient",
        error_y=(
            coefficients.loc[
                coefficients["variable"]
                != "const",
                "confidence_interval_high",
            ].values
            -
            coefficients.loc[
                coefficients["variable"]
                != "const",
                "coefficient",
            ].values
        ),
        error_y_minus=(
            coefficients.loc[
                coefficients["variable"]
                != "const",
                "coefficient",
            ].values
            -
            coefficients.loc[
                coefficients["variable"]
                != "const",
                "confidence_interval_low",
            ].values
        ),
        hover_data={
            "p_value": ":.4f",
            "standard_error": ":.4f",
            "variable_label": False,
        },
        labels={
            "variable_label": (
                "Predictor"
            ),
            "coefficient": (
                "Estimated Coefficient"
            ),
        },
    )

    coefficient_figure.add_hline(
        y=0,
        line_dash="dash",
    )

    coefficient_figure.update_layout(
        height=450,
        showlegend=False,
        xaxis_tickangle=-15,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        coefficient_figure,
        width="stretch",
    )

    display_coefficients = (
        coefficients[
            [
                "variable_label",
                "coefficient",
                "standard_error",
                "p_value",
                "confidence_interval_low",
                "confidence_interval_high",
            ]
        ]
        .rename(
            columns={
                "variable_label": (
                    "Variable"
                ),
                "coefficient": (
                    "Coefficient"
                ),
                "standard_error": (
                    "Standard Error"
                ),
                "p_value": (
                    "P-Value"
                ),
                "confidence_interval_low": (
                    "95% CI Low"
                ),
                "confidence_interval_high": (
                    "95% CI High"
                ),
            }
        )
    )

    with st.expander(
        "View regression coefficients"
    ):
        st.dataframe(
            display_coefficients,
            width="stretch",
            hide_index=True,
        )


# ============================================================
# AUTOMATED BLOCK SUMMARY
# ============================================================

if best_gain_block is not None:
    gain_text = (
        f"{best_gain_block['block_name']} produced the largest "
        f"observed gain of "
        f"{best_gain_block['absolute_improvement']:+.2f} inches."
    )
else:
    gain_text = (
        "No block had enough performance data "
        "to calculate improvement."
    )

if best_efficiency_block is not None:
    efficiency_text = (
        f"{best_efficiency_block['block_name']} had the highest "
        f"observed efficiency at "
        f"{best_efficiency_block['improvement_per_1000_load']:+.3f} "
        "inches per 1,000 load units."
    )
else:
    efficiency_text = (
        "Block efficiency could not be calculated."
    )

if best_adherence_block is not None:
    adherence_text = (
        f"{best_adherence_block['block_name']} had the highest "
        f"estimated adherence at "
        f"{best_adherence_block['adherence_percent']:.1f}%."
    )
else:
    adherence_text = (
        "Adherence could not be calculated."
    )

analysis_html = f"""
<div class="analysis-card">
    <div class="analysis-title">
        Training Block Summary
    </div>

    <div class="analysis-text">
        <strong>Largest improvement:</strong>
        {gain_text}<br><br>

        <strong>Best load efficiency:</strong>
        {efficiency_text}<br><br>

        <strong>Highest adherence:</strong>
        {adherence_text}<br><br>

        These results describe observed changes during each
        training block. They do not prove that one block or
        exercise directly caused the performance improvement.
        Differences in testing conditions, fatigue, sleep,
        soreness, and sample size may affect the results.
    </div>
</div>
"""

st.html(
    analysis_html
)


# ============================================================
# BLOCK SUMMARY TABLE
# ============================================================

with st.expander(
    "View training block summary"
):
    display_columns = [
        "block_name",
        "start_date",
        "end_date",
        "block_focus",
        "test_count",
        "starting_performance",
        "ending_performance",
        "best_performance",
        "absolute_improvement",
        "percentage_improvement",
        "completed_sessions",
        "expected_sessions",
        "adherence_percent",
        "total_training_load",
        "total_training_minutes",
        "average_rpe",
        "average_readiness",
        "average_sleep",
        "average_soreness",
        "improvement_per_1000_load",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in eligible_blocks.columns
    ]

    display_table = (
        eligible_blocks[
            available_columns
        ]
        .copy()
    )

    numeric_display_columns = [
        "starting_performance",
        "ending_performance",
        "best_performance",
        "absolute_improvement",
        "percentage_improvement",
        "expected_sessions",
        "adherence_percent",
        "total_training_load",
        "total_training_minutes",
        "average_rpe",
        "average_readiness",
        "average_sleep",
        "average_soreness",
        "improvement_per_1000_load",
    ]

    for column in numeric_display_columns:
        if column in display_table.columns:
            display_table[column] = (
                display_table[column]
                .round(2)
            )

    st.dataframe(
        display_table,
        width="stretch",
        hide_index=True,
    )