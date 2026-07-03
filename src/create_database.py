from pathlib import Path
import sqlite3
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"
DB_PATH = PROCESSED_DATA_DIR / "elevate.db"


TABLE_FILES = {
    "athletes": "athletes.csv",
    "training_blocks": "training_blocks.csv",
    "daily_wellness": "daily_wellness.csv",
    "training_sessions": "training_sessions.csv",
    "exercise_sets": "exercise_sets.csv",
    "performance_tests": "performance_tests.csv",
}


def create_database():
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, "r") as file:
        schema_sql = file.read()

    conn.executescript(schema_sql)

    for table_name, file_name in TABLE_FILES.items():
        csv_path = RAW_DATA_DIR / file_name

        if not csv_path.exists():
            raise FileNotFoundError(f"Missing CSV file: {csv_path}")

        df = pd.read_csv(csv_path)

        df.to_sql(table_name, conn, if_exists="replace", index=False)

        row_count = pd.read_sql_query(
            f"SELECT COUNT(*) AS row_count FROM {table_name}",
            conn
        )

        print(f"{table_name}: {row_count['row_count'][0]} rows loaded")

    conn.close()

    print(f"\nDatabase created successfully at: {DB_PATH}")


if __name__ == "__main__":
    create_database()