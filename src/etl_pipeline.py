from pathlib import Path
import sqlite3

import pandas as pd


# Find the main project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# File locations
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
DB_PATH = PROCESSED_DATA_DIR / "elevate.db"


def load_data():
    """Load all SQLite tables into Pandas DataFrames."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at: {DB_PATH}\n"
            "Check that the database filename and location are correct."
        )

    # Open a connection to the SQLite database
    with sqlite3.connect(DB_PATH) as connection:
        athletes_df = pd.read_sql_query(
            "SELECT * FROM athletes",
            connection
        )

        blocks_df = pd.read_sql_query(
            "SELECT * FROM training_blocks",
            connection
        )

        wellness_df = pd.read_sql_query(
            "SELECT * FROM daily_wellness",
            connection
        )

        sessions_df = pd.read_sql_query(
            "SELECT * FROM training_sessions",
            connection
        )

        exercise_df = pd.read_sql_query(
            "SELECT * FROM exercise_sets",
            connection
        )

        performance_df = pd.read_sql_query(
            "SELECT * FROM performance_tests",
            connection
        )

    return {
        "athletes": athletes_df,
        "training_blocks": blocks_df,
        "daily_wellness": wellness_df,
        "training_sessions": sessions_df,
        "exercise_sets": exercise_df,
        "performance_tests": performance_df,
    }


def validate_loaded_data(dataframes):
    """Print each DataFrame's dimensions to confirm that data loaded."""

    print("\nData successfully loaded:\n")

    for table_name, dataframe in dataframes.items():
        rows, columns = dataframe.shape

        print(
            f"{table_name}: "
            f"{rows:,} rows and {columns} columns"
        )


def main():
    dataframes = load_data()
    validate_loaded_data(dataframes)


if __name__ == "__main__":
    main()