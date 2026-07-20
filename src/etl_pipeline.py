from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "elevate.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

DAILY_FEATURE_OUTPUT = (
    OUTPUT_DIR
    / "daily_features.csv"
)

PERFORMANCE_FEATURE_OUTPUT = (
    OUTPUT_DIR
    / "performance_features.csv"
)

DATA_QUALITY_OUTPUT = (
    OUTPUT_DIR
    / "data_quality_report.csv"
)


# ============================================================
# DATABASE LOADING
# ============================================================

def load_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> pd.DataFrame:
    """
    Load a SQLite table or view into a Pandas DataFrame.
    """

    query = f"SELECT * FROM {table_name};"

    return pd.read_sql_query(
        query,
        connection,
    )


def load_database_data() -> dict[str, pd.DataFrame]:
    """
    Load the core Elevate tables from SQLite.
    """

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}\n"
            "Run python src/create_database.py first."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        data = {
            "athletes": load_table(
                connection,
                "athletes",
            ),
            "training_blocks": load_table(
                connection,
                "training_blocks",
            ),
            "daily_wellness": load_table(
                connection,
                "daily_wellness",
            ),
            "training_sessions": load_table(
                connection,
                "training_sessions",
            ),
            "exercise_sets": load_table(
                connection,
                "exercise_sets",
            ),
            "performance_tests": load_table(
                connection,
                "performance_tests",
            ),
        }

    return data


# ============================================================
# DATE AND TYPE CLEANING
# ============================================================

def clean_data_types(
    data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Convert date fields and important numeric fields into
    consistent Pandas data types.
    """

    cleaned = {
        name: dataframe.copy()
        for name, dataframe in data.items()
    }

    cleaned["training_blocks"]["start_date"] = (
        pd.to_datetime(
            cleaned["training_blocks"]["start_date"],
            errors="coerce",
        )
    )

    cleaned["training_blocks"]["end_date"] = (
        pd.to_datetime(
            cleaned["training_blocks"]["end_date"],
            errors="coerce",
        )
    )

    cleaned["daily_wellness"]["log_date"] = (
        pd.to_datetime(
            cleaned["daily_wellness"]["log_date"],
            errors="coerce",
        )
    )

    cleaned["training_sessions"]["session_date"] = (
        pd.to_datetime(
            cleaned["training_sessions"]["session_date"],
            errors="coerce",
        )
    )

    cleaned["performance_tests"]["test_date"] = (
        pd.to_datetime(
            cleaned["performance_tests"]["test_date"],
            errors="coerce",
        )
    )

    numeric_columns = {
        "daily_wellness": [
            "sleep_hours",
            "sleep_quality_1_5",
            "soreness_overall_1_10",
            "knee_pain_0_10",
            "ankle_pain_0_10",
            "energy_1_5",
            "stress_1_5",
            "motivation_1_5",
            "bodyweight_lb",
            "resting_hr",
        ],
        "training_sessions": [
            "duration_minutes",
            "intensity_rpe",
            "session_load",
            "completed",
        ],
        "exercise_sets": [
            "set_number",
            "reps",
            "weight_lb",
            "distance_yards",
            "duration_seconds",
            "jump_count",
            "perceived_difficulty_1_10",
        ],
        "performance_tests": [
            "metric_value",
            "attempts",
            "best_attempt",
            "warmup_quality_1_5",
        ],
    }

    for table_name, columns in numeric_columns.items():
        for column in columns:
            if column in cleaned[table_name].columns:
                cleaned[table_name][column] = (
                    pd.to_numeric(
                        cleaned[table_name][column],
                        errors="coerce",
                    )
                )

    return cleaned


# ============================================================
# DATA QUALITY REPORT
# ============================================================

def build_data_quality_report(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Create a table-level data-quality summary.
    """

    quality_rows: list[dict[str, object]] = []

    primary_keys = {
        "athletes": "athlete_id",
        "training_blocks": "block_id",
        "daily_wellness": "wellness_id",
        "training_sessions": "session_id",
        "exercise_sets": "set_id",
        "performance_tests": "test_id",
    }

    for table_name, dataframe in data.items():
        total_rows = len(dataframe)

        missing_values = int(
            dataframe.isna().sum().sum()
        )

        duplicate_rows = int(
            dataframe.duplicated().sum()
        )

        primary_key = primary_keys[table_name]

        duplicate_primary_keys = int(
            dataframe[primary_key]
            .duplicated()
            .sum()
        )

        invalid_date_values = 0

        date_columns = [
            column
            for column in dataframe.columns
            if column.endswith("_date")
            or column == "log_date"
        ]

        for column in date_columns:
            invalid_date_values += int(
                dataframe[column].isna().sum()
            )

        quality_rows.append(
            {
                "table_name": table_name,
                "total_rows": total_rows,
                "total_columns": len(
                    dataframe.columns
                ),
                "missing_values": missing_values,
                "duplicate_rows": duplicate_rows,
                "duplicate_primary_keys": (
                    duplicate_primary_keys
                ),
                "invalid_date_values": (
                    invalid_date_values
                ),
                "quality_status": (
                    "Pass"
                    if (
                        duplicate_rows == 0
                        and duplicate_primary_keys == 0
                        and invalid_date_values == 0
                    )
                    else "Review"
                ),
            }
        )

    return pd.DataFrame(quality_rows)


# ============================================================
# READINESS SCORE
# ============================================================

def calculate_readiness_score(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """
    Calculate a transparent readiness score from 0 to 100.

    Weights:
    - Sleep duration: 20%
    - Sleep quality: 15%
    - Energy: 20%
    - Motivation: 10%
    - Inverse stress: 15%
    - Inverse soreness: 20%
    """

    sleep_duration_score = (
        dataframe["sleep_hours"]
        .div(9.0)
        .clip(lower=0, upper=1)
        .mul(100)
    )

    sleep_quality_score = (
        dataframe["sleep_quality_1_5"]
        .sub(1)
        .div(4)
        .clip(lower=0, upper=1)
        .mul(100)
    )

    energy_score = (
        dataframe["energy_1_5"]
        .sub(1)
        .div(4)
        .clip(lower=0, upper=1)
        .mul(100)
    )

    motivation_score = (
        dataframe["motivation_1_5"]
        .sub(1)
        .div(4)
        .clip(lower=0, upper=1)
        .mul(100)
    )

    inverse_stress_score = (
        5
        - dataframe["stress_1_5"]
    ).div(4).clip(
        lower=0,
        upper=1,
    ).mul(100)

    inverse_soreness_score = (
        10
        - dataframe["soreness_overall_1_10"]
    ).div(9).clip(
        lower=0,
        upper=1,
    ).mul(100)

    readiness_score = (
        sleep_duration_score * 0.20
        + sleep_quality_score * 0.15
        + energy_score * 0.20
        + motivation_score * 0.10
        + inverse_stress_score * 0.15
        + inverse_soreness_score * 0.20
    )

    return readiness_score.round(1)


# ============================================================
# DAILY FEATURE ENGINEERING
# ============================================================

def build_daily_features(
    wellness: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create one row per athlete per wellness date.
    """

    daily_sessions = (
        sessions.loc[
            sessions["completed"] == 1
        ]
        .groupby(
            [
                "athlete_id",
                "session_date",
            ],
            as_index=False,
        )
        .agg(
            daily_training_load=(
                "session_load",
                "sum",
            ),
            daily_training_minutes=(
                "duration_minutes",
                "sum",
            ),
            sessions_completed=(
                "session_id",
                "count",
            ),
            average_session_rpe=(
                "intensity_rpe",
                "mean",
            ),
        )
        .rename(
            columns={
                "session_date": "log_date",
            }
        )
    )

    daily = wellness.merge(
        daily_sessions,
        how="left",
        on=[
            "athlete_id",
            "log_date",
        ],
        validate="one_to_one",
    )

    fill_zero_columns = [
        "daily_training_load",
        "daily_training_minutes",
        "sessions_completed",
    ]

    daily[fill_zero_columns] = (
        daily[fill_zero_columns]
        .fillna(0)
    )

    daily = daily.sort_values(
        [
            "athlete_id",
            "log_date",
        ]
    ).reset_index(drop=True)

    grouped = daily.groupby(
        "athlete_id",
        group_keys=False,
    )

    daily["previous_day_sleep_hours"] = (
        grouped["sleep_hours"].shift(1)
    )

    daily["previous_day_soreness"] = (
        grouped[
            "soreness_overall_1_10"
        ].shift(1)
    )

    daily["previous_day_training_load"] = (
        grouped[
            "daily_training_load"
        ].shift(1)
    )

    daily["seven_day_training_load"] = (
        grouped[
            "daily_training_load"
        ]
        .rolling(
            window=7,
            min_periods=1,
        )
        .sum()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    daily["twenty_eight_day_training_load"] = (
        grouped[
            "daily_training_load"
        ]
        .rolling(
            window=28,
            min_periods=1,
        )
        .sum()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    daily["twenty_eight_day_weekly_average"] = (
        daily[
            "twenty_eight_day_training_load"
        ]
        / 4.0
    )

    daily["load_spike_ratio"] = np.where(
        daily.index.to_series()
        .groupby(daily["athlete_id"])
        .cumcount()
        >= 27,
        daily["seven_day_training_load"]
        / daily[
            "twenty_eight_day_weekly_average"
        ].replace(0, np.nan),
        np.nan,
    )

    daily["readiness_score"] = (
        calculate_readiness_score(daily)
    )

    high_pain = (
        (daily["knee_pain_0_10"] >= 6)
        | (daily["ankle_pain_0_10"] >= 6)
    )

    prioritize_recovery = (
        high_pain
        | (daily["readiness_score"] < 50)
    )

    modify_training = (
        (daily["readiness_score"] < 70)
        | (
            daily[
                "soreness_overall_1_10"
            ]
            >= 7
        )
        | (
            daily["load_spike_ratio"]
            >= 1.50
        )
    )

    daily["recommendation"] = np.select(
        [
            prioritize_recovery,
            modify_training,
        ],
        [
            "Prioritize Recovery",
            "Modify Training",
        ],
        default="Train Hard",
    )

    daily["recommendation_reason"] = np.select(
        [
            high_pain,
            daily["readiness_score"] < 50,
            (
                daily[
                    "soreness_overall_1_10"
                ]
                >= 7
            ),
            daily["load_spike_ratio"] >= 1.50,
            daily["readiness_score"] < 70,
        ],
        [
            "High pain score reported",
            "Low readiness score",
            "High overall soreness",
            "Recent training load is elevated",
            "Moderate readiness score",
        ],
        default=(
            "Recovery indicators support "
            "normal training"
        ),
    )

    daily["low_sleep_flag"] = (
        daily["sleep_hours"] < 7
    )

    daily["high_soreness_flag"] = (
        daily["soreness_overall_1_10"]
        >= 7
    )

    daily["pain_flag"] = high_pain

    daily["load_spike_flag"] = (
        daily["load_spike_ratio"]
        >= 1.50
    )

    return daily


# ============================================================
# PERFORMANCE FEATURE ENGINEERING
# ============================================================

def build_performance_features(
    performance_tests: pd.DataFrame,
    daily_features: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create one row per performance-test record with trends,
    recovery data, and previous-session information.
    """

    performance = performance_tests.copy()

    performance = performance.sort_values(
        [
            "athlete_id",
            "metric_name",
            "test_date",
            "test_id",
        ]
    ).reset_index(drop=True)

    grouped = performance.groupby(
        [
            "athlete_id",
            "metric_name",
        ],
        group_keys=False,
    )

    performance[
        "previous_test_value"
    ] = grouped[
        "metric_value"
    ].shift(1)

    performance[
        "change_from_previous_test"
    ] = (
        performance["metric_value"]
        - performance[
            "previous_test_value"
        ]
    )

    performance[
        "three_test_rolling_average"
    ] = (
        grouped["metric_value"]
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
        .reset_index(
            level=[0, 1],
            drop=True,
        )
        .round(2)
    )

    performance[
        "personal_best_to_date"
    ] = grouped[
        "metric_value"
    ].cummax()

    performance["personal_best_flag"] = (
        performance["metric_value"]
        == performance[
            "personal_best_to_date"
        ]
    )

    baseline_values = (
        performance.groupby(
            [
                "athlete_id",
                "metric_name",
            ]
        )["metric_value"]
        .transform("first")
    )

    performance[
        "baseline_value"
    ] = baseline_values

    performance[
        "change_from_baseline"
    ] = (
        performance["metric_value"]
        - performance["baseline_value"]
    )

    performance[
        "percent_change_from_baseline"
    ] = (
        performance[
            "change_from_baseline"
        ]
        / performance[
            "baseline_value"
        ].replace(0, np.nan)
        * 100
    ).round(2)

    same_day_recovery = (
        daily_features[
            [
                "athlete_id",
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
                "seven_day_training_load",
                "twenty_eight_day_training_load",
                "load_spike_ratio",
                "recommendation",
            ]
        ]
        .rename(
            columns={
                "log_date": "test_date",
            }
        )
    )

    performance = performance.merge(
        same_day_recovery,
        how="left",
        on=[
            "athlete_id",
            "test_date",
        ],
        validate="many_to_one",
    )

    previous_night_sleep = (
        daily_features[
            [
                "athlete_id",
                "log_date",
                "sleep_hours",
                "sleep_quality_1_5",
            ]
        ]
        .copy()
    )

    previous_night_sleep[
        "test_date"
    ] = (
        previous_night_sleep[
            "log_date"
        ]
        + pd.Timedelta(days=1)
    )

    previous_night_sleep = (
        previous_night_sleep.rename(
            columns={
                "sleep_hours": (
                    "previous_night_sleep_hours"
                ),
                "sleep_quality_1_5": (
                    "previous_night_sleep_quality"
                ),
            }
        )
        .drop(columns="log_date")
    )

    performance = performance.merge(
        previous_night_sleep,
        how="left",
        on=[
            "athlete_id",
            "test_date",
        ],
        validate="many_to_one",
    )

        # Keep only completed sessions.
    completed_sessions = sessions.loc[
        sessions["completed"] == 1
    ].copy()

    # Rename session columns before performing the as-of merge.
    completed_sessions = completed_sessions.rename(
        columns={
            "session_date": "previous_session_date",
            "session_type": "previous_session_type",
            "session_focus": "previous_session_focus",
            "duration_minutes": "previous_session_duration",
            "intensity_rpe": "previous_session_rpe",
            "session_load": "previous_session_load",
        }
    )

    # merge_asof requires the merge date to be globally sorted.
    #
    # Sort by the date column FIRST, followed by athlete ID.
    # Sorting by athlete ID first causes the dates to restart for
    # each athlete, which triggers "left keys must be sorted."
    performance = performance.sort_values(
        [
            "test_date",
            "athlete_id",
            "test_id",
        ]
    ).reset_index(drop=True)

    completed_sessions = completed_sessions.sort_values(
        [
            "previous_session_date",
            "athlete_id",
            "session_id",
        ]
    ).reset_index(drop=True)

    performance = pd.merge_asof(
        left=performance,
        right=completed_sessions[
            [
                "athlete_id",
                "previous_session_date",
                "previous_session_type",
                "previous_session_focus",
                "previous_session_duration",
                "previous_session_rpe",
                "previous_session_load",
            ]
        ],
        left_on="test_date",
        right_on="previous_session_date",
        by="athlete_id",
        direction="backward",
        allow_exact_matches=False,
    )

    performance["days_since_previous_session"] = (
        performance["test_date"]
        - performance["previous_session_date"]
    ).dt.days

    # Restore a more useful analytical order after the merge.
    performance = performance.sort_values(
        [
            "athlete_id",
            "metric_name",
            "test_date",
            "test_id",
        ]
    ).reset_index(drop=True)

    return performance

# ============================================================
# PIPELINE EXECUTION
# ============================================================

def run_pipeline() -> None:
    """
    Run the complete Day 6 Pandas pipeline.
    """

    print("Loading Elevate database...")

    raw_data = load_database_data()

    print("Cleaning data types...")

    clean_data = clean_data_types(
        raw_data
    )

    print("Building data-quality report...")

    quality_report = (
        build_data_quality_report(
            clean_data
        )
    )

    print("Building daily feature set...")

    daily_features = build_daily_features(
        wellness=clean_data[
            "daily_wellness"
        ],
        sessions=clean_data[
            "training_sessions"
        ],
    )

    print("Building performance feature set...")

    performance_features = (
        build_performance_features(
            performance_tests=clean_data[
                "performance_tests"
            ],
            daily_features=daily_features,
            sessions=clean_data[
                "training_sessions"
            ],
        )
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    quality_report.to_csv(
        DATA_QUALITY_OUTPUT,
        index=False,
    )

    daily_features.to_csv(
        DAILY_FEATURE_OUTPUT,
        index=False,
    )

    performance_features.to_csv(
        PERFORMANCE_FEATURE_OUTPUT,
        index=False,
    )

    print("\nPipeline complete.")

    print(
        f"- Data quality report: "
        f"{DATA_QUALITY_OUTPUT}"
    )

    print(
        f"- Daily features: "
        f"{DAILY_FEATURE_OUTPUT}"
    )

    print(
        f"- Performance features: "
        f"{PERFORMANCE_FEATURE_OUTPUT}"
    )

    print("\nOutput dimensions:")

    print(
        f"- Data quality report: "
        f"{quality_report.shape}"
    )

    print(
        f"- Daily features: "
        f"{daily_features.shape}"
    )

    print(
        f"- Performance features: "
        f"{performance_features.shape}"
    )

    print("\nReadiness score range:")

    print(
        daily_features[
            "readiness_score"
        ].min(),
        "to",
        daily_features[
            "readiness_score"
        ].max(),
    )


if __name__ == "__main__":
    run_pipeline()