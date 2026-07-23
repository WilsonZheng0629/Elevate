from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DAILY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "daily_features.csv"
)

PERFORMANCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "performance_features.csv"
)


def test_readiness_range() -> None:
    daily = pd.read_csv(DAILY_PATH)

    assert daily["readiness_score"].between(
        0,
        100,
    ).all()


def test_training_load_nonnegative() -> None:
    daily = pd.read_csv(DAILY_PATH)

    assert (
        daily["daily_training_load"] >= 0
    ).all()

    assert (
        daily["seven_day_training_load"] >= 0
    ).all()


def test_valid_recommendations() -> None:
    daily = pd.read_csv(DAILY_PATH)

    valid_values = {
        "Train Hard",
        "Modify Training",
        "Prioritize Recovery",
    }

    actual_values = set(
        daily["recommendation"]
        .dropna()
        .unique()
    )

    assert actual_values.issubset(
        valid_values
    )


def test_previous_session_days_nonnegative() -> None:
    performance = pd.read_csv(
        PERFORMANCE_PATH
    )

    values = performance[
        "days_since_previous_session"
    ].dropna()

    assert (values >= 0).all()


def test_expected_performance_metrics() -> None:
    performance = pd.read_csv(
        PERFORMANCE_PATH
    )

    expected_metrics = {
        "approach_touch",
        "approach_vertical",
        "standing_touch",
        "standing_vertical",
    }

    actual_metrics = set(
        performance["metric_name"]
        .dropna()
        .unique()
    )

    assert expected_metrics.issubset(
        actual_metrics
    )


def test_unique_performance_test_ids() -> None:
    performance = pd.read_csv(
        PERFORMANCE_PATH
    )

    assert not performance[
        "test_id"
    ].duplicated().any()