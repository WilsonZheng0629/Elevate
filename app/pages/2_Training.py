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
    page_title="Elevate | Training",
    page_icon="🏋️",
    layout="wide",
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "elevate.db"
)

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

TRAINING_SESSIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "training_sessions.csv"
)

EXERCISE_SETS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "exercise_sets.csv"
)

TRAINING_BLOCKS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "training_blocks.csv"
)


# ============================================================
# STYLING
# ============================================================

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

        .insight-card {
            border-radius: 14px;
            padding: 18px;
            margin-top: 8px;
            margin-bottom: 16px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background-color: rgba(255, 255, 255, 0.04);
        }

        .insight-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .insight-text {
            opacity: 0.85;
            line-height: 1.5;
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
    pd.DataFrame,
]:
    required_files = [
        DAILY_FEATURES_PATH,
        PERFORMANCE_FEATURES_PATH,
        TRAINING_SESSIONS_PATH,
        EXERCISE_SETS_PATH,
        TRAINING_BLOCKS_PATH,
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
            "The following required files were not found:\n"
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

    sessions = pd.read_csv(
        TRAINING_SESSIONS_PATH,
        parse_dates=["session_date"],
    )

    exercise_sets = pd.read_csv(
        EXERCISE_SETS_PATH,
    )

    blocks = pd.read_csv(
        TRAINING_BLOCKS_PATH,
        parse_dates=[
            "start_date",
            "end_date",
        ],
    )

    return (
        daily,
        performance,
        sessions,
        exercise_sets,
        blocks,
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_session_type(session_type: str) -> str:
    return (
        str(session_type)
        .replace("_", " ")
        .title()
    )


def calculate_weekly_training(
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    if sessions.empty:
        return pd.DataFrame()

    weekly = (
        sessions
        .set_index("session_date")
        .resample("W-MON")
        .agg(
            weekly_training_load=(
                "session_load",
                "sum",
            ),
            weekly_training_minutes=(
                "duration_minutes",
                "sum",
            ),
            weekly_sessions=(
                "session_id",
                "count",
            ),
            average_rpe=(
                "intensity_rpe",
                "mean",
            ),
        )
        .reset_index()
        .rename(
            columns={
                "session_date": "week_start",
            }
        )
    )

    weekly["average_rpe"] = (
        weekly["average_rpe"].round(1)
    )

    return weekly


def build_exercise_summary(
    sessions: pd.DataFrame,
    exercise_sets: pd.DataFrame,
) -> pd.DataFrame:
    if sessions.empty or exercise_sets.empty:
        return pd.DataFrame()

    selected_session_ids = (
        sessions["session_id"]
        .dropna()
        .unique()
    )

    filtered_sets = exercise_sets.loc[
        exercise_sets["session_id"]
        .isin(selected_session_ids)
    ].copy()

    if filtered_sets.empty:
        return pd.DataFrame()

    filtered_sets["volume_lb"] = (
        filtered_sets["weight_lb"]
        .fillna(0)
        * filtered_sets["reps"].fillna(0)
    )

    summary = (
        filtered_sets
        .groupby(
            "exercise_name",
            as_index=False,
        )
        .agg(
            sessions_exposed=(
                "session_id",
                "nunique",
            ),
            total_sets=(
                "set_id",
                "count",
            ),
            total_reps=(
                "reps",
                "sum",
            ),
            total_volume_lb=(
                "volume_lb",
                "sum",
            ),
            total_jump_contacts=(
                "jump_count",
                "sum",
            ),
            average_difficulty=(
                "perceived_difficulty_1_10",
                "mean",
            ),
        )
    )

    summary["average_difficulty"] = (
        summary["average_difficulty"].round(1)
    )

    summary["total_volume_lb"] = (
        summary["total_volume_lb"].round(0)
    )

    summary = summary.sort_values(
        [
            "sessions_exposed",
            "total_sets",
        ],
        ascending=False,
    )

    return summary


def build_session_type_response(
    performance: pd.DataFrame,
) -> pd.DataFrame:
    required_columns = {
        "previous_session_type",
        "change_from_previous_test",
    }

    if (
        performance.empty
        or not required_columns.issubset(
            performance.columns
        )
    ):
        return pd.DataFrame()

    response = (
        performance
        .dropna(
            subset=[
                "previous_session_type",
                "change_from_previous_test",
            ]
        )
        .groupby(
            "previous_session_type",
            as_index=False,
        )
        .agg(
            test_count=(
                "test_id",
                "count",
            ),
            average_next_test_change=(
                "change_from_previous_test",
                "mean",
            ),
            median_next_test_change=(
                "change_from_previous_test",
                "median",
            ),
            average_previous_session_load=(
                "previous_session_load",
                "mean",
            ),
        )
    )

    response[
        "average_next_test_change"
    ] = response[
        "average_next_test_change"
    ].round(2)

    response[
        "median_next_test_change"
    ] = response[
        "median_next_test_change"
    ].round(2)

    response[
        "average_previous_session_load"
    ] = response[
        "average_previous_session_load"
    ].round(0)

    return response.sort_values(
        "average_next_test_change",
        ascending=False,
    )


# ============================================================
# LOAD DATA
# ============================================================

try:
    (
        daily_features,
        performance_features,
        training_sessions,
        exercise_sets,
        training_blocks,
    ) = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()


# ============================================================
# PAGE HEADER
# ============================================================

st.title("Training Analysis")

st.caption(
    "Understand how training volume, intensity, session type, "
    "and exercise exposure relate to performance."
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================

athlete_ids = sorted(
    training_sessions["athlete_id"]
    .dropna()
    .unique()
    .tolist()
)

selected_athlete = st.sidebar.selectbox(
    "Athlete",
    options=athlete_ids,
)

athlete_sessions = (
    training_sessions.loc[
        training_sessions["athlete_id"]
        == selected_athlete
    ]
    .copy()
    .sort_values("session_date")
)

athlete_performance = (
    performance_features.loc[
        performance_features["athlete_id"]
        == selected_athlete
    ]
    .copy()
)

athlete_blocks = (
    training_blocks.loc[
        training_blocks["athlete_id"]
        == selected_athlete
    ]
    .copy()
    .sort_values("start_date")
)

if athlete_sessions.empty:
    st.warning(
        "No training-session data is available for this athlete."
    )
    st.stop()

minimum_date = (
    athlete_sessions["session_date"]
    .min()
    .date()
)

maximum_date = (
    athlete_sessions["session_date"]
    .max()
    .date()
)

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
    start_date, end_date = (
        minimum_date,
        maximum_date,
    )

session_types = sorted(
    athlete_sessions["session_type"]
    .dropna()
    .unique()
    .tolist()
)

selected_session_types = st.sidebar.multiselect(
    "Session types",
    options=session_types,
    default=session_types,
    format_func=format_session_type,
)

block_options = {
    "All blocks": None,
}

for _, block in athlete_blocks.iterrows():
    block_options[
        block["block_name"]
    ] = block["block_id"]

selected_block_name = st.sidebar.selectbox(
    "Training block",
    options=list(block_options.keys()),
)

selected_block_id = block_options[
    selected_block_name
]

selected_metric = st.sidebar.selectbox(
    "Performance metric",
    options=[
        "approach_vertical",
        "standing_vertical",
    ],
    format_func=lambda value: (
        value.replace("_", " ").title()
    ),
)


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_sessions = athlete_sessions.loc[
    athlete_sessions["session_date"]
    .dt.date
    .between(
        start_date,
        end_date,
    )
].copy()

if selected_session_types:
    filtered_sessions = filtered_sessions.loc[
        filtered_sessions["session_type"]
        .isin(selected_session_types)
    ].copy()
else:
    filtered_sessions = filtered_sessions.iloc[0:0]

if selected_block_id is not None:
    filtered_sessions = filtered_sessions.loc[
        filtered_sessions["block_id"]
        == selected_block_id
    ].copy()

filtered_sessions = filtered_sessions.loc[
    filtered_sessions["completed"] == 1
].copy()

filtered_performance = athlete_performance.loc[
    athlete_performance["metric_name"]
    == selected_metric
].copy()

filtered_performance = filtered_performance.loc[
    filtered_performance["test_date"]
    .dt.date
    .between(
        start_date,
        end_date,
    )
].copy()

if selected_block_id is not None:
    filtered_performance = (
        filtered_performance.loc[
            filtered_performance["block_id"]
            == selected_block_id
        ]
        .copy()
    )

if filtered_sessions.empty:
    st.warning(
        "No completed sessions match the selected filters."
    )
    st.stop()


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_sessions = len(filtered_sessions)

total_training_load = float(
    filtered_sessions["session_load"].sum()
)

total_training_minutes = float(
    filtered_sessions["duration_minutes"].sum()
)

average_session_rpe = float(
    filtered_sessions["intensity_rpe"].mean()
)

average_session_load = float(
    filtered_sessions["session_load"].mean()
)

training_days = (
    filtered_sessions["session_date"]
    .dt.date
    .nunique()
)

date_span_days = (
    end_date - start_date
).days + 1

weeks_in_range = max(
    date_span_days / 7,
    1,
)

sessions_per_week = (
    total_sessions / weeks_in_range
)


# ============================================================
# KPI CARDS
# ============================================================

kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4 = (
    st.columns(4)
)

with kpi_col_1:
    st.metric(
        "Completed Sessions",
        f"{total_sessions}",
        delta=(
            f"{sessions_per_week:.1f} per week"
        ),
    )

with kpi_col_2:
    st.metric(
        "Total Training Load",
        f"{total_training_load:,.0f}",
    )

with kpi_col_3:
    st.metric(
        "Training Time",
        f"{total_training_minutes / 60:.1f} hrs",
    )

with kpi_col_4:
    st.metric(
        "Average Session RPE",
        f"{average_session_rpe:.1f}/10",
    )


# ============================================================
# WEEKLY TRAINING LOAD
# ============================================================

st.subheader("Weekly Training Load")

weekly_training = calculate_weekly_training(
    filtered_sessions
)

weekly_figure = go.Figure()

weekly_figure.add_trace(
    go.Bar(
        x=weekly_training["week_start"],
        y=weekly_training[
            "weekly_training_load"
        ],
        name="Weekly load",
        customdata=weekly_training[
            [
                "weekly_sessions",
                "weekly_training_minutes",
                "average_rpe",
            ]
        ],
        hovertemplate=(
            "Week: %{x|%b %d, %Y}"
            "<br>Training load: %{y:.0f}"
            "<br>Sessions: %{customdata[0]}"
            "<br>Minutes: %{customdata[1]:.0f}"
            "<br>Average RPE: %{customdata[2]:.1f}"
            "<extra></extra>"
        ),
    )
)

weekly_figure.add_trace(
    go.Scatter(
        x=weekly_training["week_start"],
        y=weekly_training[
            "weekly_training_load"
        ].rolling(
            window=4,
            min_periods=1,
        ).mean(),
        mode="lines",
        name="4-week rolling average",
        line={
            "dash": "dash",
        },
    )
)

weekly_figure.update_layout(
    height=450,
    xaxis_title="Week",
    yaxis_title="Training Load",
    hovermode="x unified",
    legend_title=None,
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)

st.plotly_chart(
    weekly_figure,
    width="stretch",
)


# ============================================================
# SESSION-TYPE DISTRIBUTION
# ============================================================

left_col, right_col = st.columns(2)

session_type_summary = (
    filtered_sessions
    .groupby(
        "session_type",
        as_index=False,
    )
    .agg(
        session_count=(
            "session_id",
            "count",
        ),
        total_training_load=(
            "session_load",
            "sum",
        ),
        total_minutes=(
            "duration_minutes",
            "sum",
        ),
        average_rpe=(
            "intensity_rpe",
            "mean",
        ),
    )
)

session_type_summary[
    "session_type_label"
] = session_type_summary[
    "session_type"
].apply(
    format_session_type
)

with left_col:
    st.subheader("Load by Session Type")

    load_by_type_figure = px.bar(
        session_type_summary.sort_values(
            "total_training_load",
            ascending=False,
        ),
        x="session_type_label",
        y="total_training_load",
        hover_data={
            "session_count": True,
            "total_minutes": True,
            "average_rpe": ":.1f",
            "session_type_label": False,
        },
        labels={
            "session_type_label": (
                "Session Type"
            ),
            "total_training_load": (
                "Training Load"
            ),
        },
    )

    load_by_type_figure.update_layout(
        height=420,
        showlegend=False,
        xaxis_tickangle=-25,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        load_by_type_figure,
        width="stretch",
    )

with right_col:
    st.subheader("Training Time Distribution")

    time_distribution_figure = px.pie(
        session_type_summary,
        names="session_type_label",
        values="total_minutes",
        hole=0.55,
    )

    time_distribution_figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )

    time_distribution_figure.update_layout(
        height=420,
        legend_title=None,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        time_distribution_figure,
        width="stretch",
    )


# ============================================================
# EXERCISE EXPOSURE
# ============================================================

st.subheader("Exercise Exposure")

exercise_summary = build_exercise_summary(
    filtered_sessions,
    exercise_sets,
)

if exercise_summary.empty:
    st.info(
        "No exercise-set records exist for the selected filters."
    )
else:
    exercise_chart_data = (
        exercise_summary
        .head(15)
        .sort_values(
            "sessions_exposed",
            ascending=True,
        )
    )

    exercise_figure = px.bar(
        exercise_chart_data,
        x="sessions_exposed",
        y="exercise_name",
        orientation="h",
        hover_data={
            "total_sets": True,
            "total_reps": True,
            "total_volume_lb": ":,.0f",
            "total_jump_contacts": True,
            "average_difficulty": ":.1f",
            "sessions_exposed": False,
        },
        labels={
            "sessions_exposed": (
                "Sessions Containing Exercise"
            ),
            "exercise_name": "Exercise",
        },
    )

    exercise_figure.update_layout(
        height=520,
        showlegend=False,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        exercise_figure,
        width="stretch",
    )


# ============================================================
# STRENGTH VOLUME AND JUMP CONTACTS
# ============================================================

left_col, right_col = st.columns(2)

selected_session_ids = (
    filtered_sessions["session_id"]
    .dropna()
    .unique()
)

filtered_exercise_sets = exercise_sets.loc[
    exercise_sets["session_id"]
    .isin(selected_session_ids)
].copy()

filtered_exercise_sets = (
    filtered_exercise_sets.merge(
        filtered_sessions[
            [
                "session_id",
                "session_date",
            ]
        ],
        how="left",
        on="session_id",
        validate="many_to_one",
    )
)

filtered_exercise_sets[
    "strength_volume_lb"
] = (
    filtered_exercise_sets["weight_lb"]
    .fillna(0)
    * filtered_exercise_sets["reps"]
    .fillna(0)
)

weekly_exercise_metrics = (
    filtered_exercise_sets
    .set_index("session_date")
    .resample("W-MON")
    .agg(
        weekly_strength_volume_lb=(
            "strength_volume_lb",
            "sum",
        ),
        weekly_jump_contacts=(
            "jump_count",
            "sum",
        ),
    )
    .reset_index()
    .rename(
        columns={
            "session_date": "week_start",
        }
    )
)

with left_col:
    st.subheader("Weekly Strength Volume")

    strength_volume_figure = px.bar(
        weekly_exercise_metrics,
        x="week_start",
        y="weekly_strength_volume_lb",
        labels={
            "week_start": "Week",
            "weekly_strength_volume_lb": (
                "Volume Load (lb × reps)"
            ),
        },
    )

    strength_volume_figure.update_layout(
        height=400,
        showlegend=False,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        strength_volume_figure,
        width="stretch",
    )

with right_col:
    st.subheader("Weekly Jump Contacts")

    jump_contact_figure = px.bar(
        weekly_exercise_metrics,
        x="week_start",
        y="weekly_jump_contacts",
        labels={
            "week_start": "Week",
            "weekly_jump_contacts": (
                "Jump Contacts"
            ),
        },
    )

    jump_contact_figure.update_layout(
        height=400,
        showlegend=False,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        jump_contact_figure,
        width="stretch",
    )


# ============================================================
# SESSION-TYPE RESPONSE
# ============================================================

st.subheader("Performance Following Session Types")

session_response = build_session_type_response(
    filtered_performance
)

if session_response.empty:
    st.info(
        "There is not enough matched performance and "
        "previous-session data for this analysis."
    )
else:
    session_response[
        "session_type_label"
    ] = session_response[
        "previous_session_type"
    ].apply(
        format_session_type
    )

    response_figure = px.bar(
        session_response,
        x="session_type_label",
        y="average_next_test_change",
        hover_data={
            "test_count": True,
            "median_next_test_change": ":.2f",
            "average_previous_session_load": ":.0f",
            "session_type_label": False,
        },
        labels={
            "session_type_label": (
                "Previous Session Type"
            ),
            "average_next_test_change": (
                "Average Change in Next Test (in)"
            ),
        },
    )

    response_figure.add_hline(
        y=0,
        line_dash="dash",
    )

    response_figure.update_layout(
        height=430,
        showlegend=False,
        xaxis_tickangle=-25,
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        response_figure,
        width="stretch",
    )

    st.caption(
        "This chart shows the average change in the next "
        "performance test following each session type. It shows "
        "association only and does not prove causation."
    )


# ============================================================
# AUTOMATED INSIGHT
# ============================================================

largest_load_type_row = (
    session_type_summary.sort_values(
        "total_training_load",
        ascending=False,
    )
    .iloc[0]
)

largest_load_type = format_session_type(
    largest_load_type_row[
        "session_type"
    ]
)

largest_load_share = (
    largest_load_type_row[
        "total_training_load"
    ]
    / total_training_load
    * 100
    if total_training_load > 0
    else 0
)

if not exercise_summary.empty:
    most_exposed_exercise = (
        exercise_summary.iloc[0][
            "exercise_name"
        ]
    )

    most_exposed_sessions = int(
        exercise_summary.iloc[0][
            "sessions_exposed"
        ]
    )
else:
    most_exposed_exercise = "No exercise data"
    most_exposed_sessions = 0

if not session_response.empty:
    best_response_row = (
        session_response.iloc[0]
    )

    best_response_type = format_session_type(
        best_response_row[
            "previous_session_type"
        ]
    )

    best_response_change = (
        best_response_row[
            "average_next_test_change"
        ]
    )

    response_text = (
        f"{best_response_type} sessions were followed by the "
        f"largest average test change "
        f"({best_response_change:+.2f} inches), based on "
        f"{int(best_response_row['test_count'])} matched tests."
    )
else:
    response_text = (
        "There is not yet enough matched test data to compare "
        "performance responses by session type."
    )

insight_html = f"""
<div class="insight-card">
    <div class="insight-title">Training Summary</div>
    <div class="insight-text">
        <strong>Largest workload source:</strong>
        {largest_load_type} accounted for
        {largest_load_share:.1f}% of total training load.
        <br><br>
        <strong>Most frequent exercise:</strong>
        {most_exposed_exercise} appeared in
        {most_exposed_sessions} sessions.
        <br><br>
        <strong>Observed performance response:</strong>
        {response_text}
        <br><br>
        Exercise and session-type results describe associations,
        not proof that a specific training method caused the
        performance change.
    </div>
</div>
"""

st.html(insight_html)


# ============================================================
# TRAINING DETAIL TABLE
# ============================================================

with st.expander("View training-session records"):
    display_columns = [
        "session_date",
        "block_id",
        "session_type",
        "session_focus",
        "duration_minutes",
        "intensity_rpe",
        "session_load",
        "location",
        "completed",
        "notes",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in filtered_sessions.columns
    ]

    training_table = (
        filtered_sessions[
            available_columns
        ]
        .sort_values(
            "session_date",
            ascending=False,
        )
        .copy()
    )

    st.dataframe(
        training_table,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# EXERCISE DETAIL TABLE
# ============================================================

with st.expander("View exercise exposure details"):
    if exercise_summary.empty:
        st.info(
            "No exercise exposure data is available."
        )
    else:
        st.dataframe(
            exercise_summary,
            width="stretch",
            hide_index=True,
        )