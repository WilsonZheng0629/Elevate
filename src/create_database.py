from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd




# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

DATABASE_PATH = PROCESSED_DATA_DIR / "elevate.db"

SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
ANALYTICS_VIEWS_PATH = PROJECT_ROOT / "sql" / "analytics_views.sql"

print("\nPATH CHECK")
print(f"Project root: {PROJECT_ROOT}")
print(f"Schema file: {SCHEMA_PATH}")
print(f"Views file: {ANALYTICS_VIEWS_PATH}")
print(f"Database file: {DATABASE_PATH}")
print(f"Schema exists: {SCHEMA_PATH.exists()}")
print(f"Views file exists: {ANALYTICS_VIEWS_PATH.exists()}")

# ============================================================
# TABLE LOAD ORDER
# Parent tables must be inserted before child tables.
# ============================================================

TABLE_FILES = {
    "athletes": "athletes.csv",
    "training_blocks": "training_blocks.csv",
    "daily_wellness": "daily_wellness.csv",
    "training_sessions": "training_sessions.csv",
    "exercise_sets": "exercise_sets.csv",
    "performance_tests": "performance_tests.csv",
}


# ============================================================
# DATA CLEANING
# ============================================================

def clean_dataframe(
    table_name: str,
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply table-specific cleaning before records are inserted.

    The function returns a cleaned copy so the original CSV files
    are not modified.
    """

    df = dataframe.copy()

    # Standardize column names.
    df.columns = [
        column.strip()
        for column in df.columns
    ]

    # Convert empty strings and whitespace-only strings to NULL.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    if table_name == "exercise_sets":
        if "weight_lb" in df.columns:
            negative_weight_mask = (
                df["weight_lb"].notna()
                & (df["weight_lb"] < 0)
            )

            negative_weight_count = int(
                negative_weight_mask.sum()
            )

            if negative_weight_count > 0:
                print(
                    f"Warning: {negative_weight_count} negative "
                    "weight_lb values were found in exercise_sets. "
                    "They will be replaced with NULL."
                )

                df.loc[
                    negative_weight_mask,
                    "weight_lb",
                ] = pd.NA

    return df


# ============================================================
# SOURCE FILE VALIDATION
# ============================================================

def validate_source_files() -> None:
    """
    Confirm that all required SQL and CSV files exist.
    """

    missing_files: list[Path] = []

    if not SCHEMA_PATH.exists():
        missing_files.append(SCHEMA_PATH)

    for filename in TABLE_FILES.values():
        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            missing_files.append(file_path)

    if missing_files:
        formatted_paths = "\n".join(
            f"- {path}"
            for path in missing_files
        )

        raise FileNotFoundError(
            "The following required files are missing:\n"
            f"{formatted_paths}"
        )


# ============================================================
# DATABASE VALIDATION
# ============================================================

def validate_database(
    connection: sqlite3.Connection,
) -> None:
    """
    Run SQLite integrity, foreign-key, and row-count checks.
    """

    integrity_result = connection.execute(
        "PRAGMA integrity_check;"
    ).fetchone()

    if integrity_result is None:
        raise RuntimeError(
            "SQLite did not return an integrity-check result."
        )

    if integrity_result[0] != "ok":
        raise RuntimeError(
            "Database integrity check failed: "
            f"{integrity_result[0]}"
        )

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check;"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            "Foreign-key validation failed. Errors:\n"
            f"{foreign_key_errors}"
        )

    print("\nDatabase validation results:")

    for table_name in TABLE_FILES:
        row_count = connection.execute(
            f"SELECT COUNT(*) FROM {table_name};"
        ).fetchone()[0]

        print(
            f"- {table_name}: {row_count:,} rows"
        )

    print("- SQLite integrity check: passed")
    print("- Foreign-key check: passed")


# ============================================================
# DATABASE CREATION
# ============================================================

def create_database() -> None:
    """
    Create a fresh SQLite database using schema.sql, load the CSV
    data with append mode, create analytical views, and validate
    the final database.
    """

    validate_source_files()

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove the old database before rebuilding.
    #
    # This is necessary because the script uses append mode.
    # Otherwise, rerunning the script would duplicate records.
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

        print(
            f"Deleted existing database: {DATABASE_PATH}"
        )

    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(DATABASE_PATH)

        # Foreign-key enforcement must be enabled for each
        # SQLite connection.
        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        # Create all tables, constraints, and indexes.
        schema_sql = SCHEMA_PATH.read_text(
            encoding="utf-8"
        )

        connection.executescript(schema_sql)

        print("\nDatabase schema created successfully.")

        # Load tables in dependency order.
        for table_name, filename in TABLE_FILES.items():
            csv_path = RAW_DATA_DIR / filename

            dataframe = pd.read_csv(csv_path)

            dataframe = clean_dataframe(
                table_name=table_name,
                dataframe=dataframe,
            )

            dataframe.to_sql(
                name=table_name,
                con=connection,
                if_exists="append",
                index=False,
            )

            print(
                f"Loaded {len(dataframe):,} rows "
                f"into {table_name}."
            )

        # Create analytical views when the file exists.
        #
        # You may not have this file yet. The database can still
        # be created before Day 5 is completed.
        if ANALYTICS_VIEWS_PATH.exists():
            analytics_sql = (
                ANALYTICS_VIEWS_PATH.read_text(
                    encoding="utf-8"
                )
            )

            connection.executescript(
                analytics_sql
            )

            print(
                "\nAnalytical views created successfully."
            )
        else:
            print(
                "\nNote: sql/analytics_views.sql was not found. "
                "Skipping analytical-view creation for now."
            )

        connection.commit()

        validate_database(connection)

    except Exception:
        if connection is not None:
            connection.rollback()

        # Remove the incomplete database so it cannot be confused
        # with a successful build.
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()

        raise

    finally:
        if connection is not None:
            connection.close()

    print(
        "\nDatabase created and validated successfully:"
    )
    print(DATABASE_PATH)


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    create_database()