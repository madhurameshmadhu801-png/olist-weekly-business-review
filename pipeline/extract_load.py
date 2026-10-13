"""Extract raw CSV datasets and load verbatim into raw_* SQLite tables."""
import sqlite3
import sys
from pathlib import Path
import pandas as pd

from pipeline.config import DB_PATH, RAW_DIR, RAW_TABLE_SCHEMAS
from pipeline.logging_setup import log_step, setup_logger

logger = setup_logger("extract_load")


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Creates a connection to SQLite with WAL mode and fast pragmas."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def extract_and_load(db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> dict[str, int]:
    """Validates schemas and loads all 9 CSV files into raw_* SQLite tables idempotently."""
    logger.info("Starting raw data extraction and loading...")
    row_counts = {}

    if not raw_dir.exists():
        msg = f"Raw data directory does not exist: {raw_dir}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    conn = get_db_connection(db_path)

    try:
        for filename, spec in RAW_TABLE_SCHEMAS.items():
            file_path = raw_dir / filename
            table_name = spec["table"]
            expected_columns = spec["expected_columns"]

            step_label = f"Ingesting {filename} -> {table_name}"
            with log_step(logger, step_label):
                # 1. Validate file presence
                if not file_path.exists():
                    msg = f"Critical Error: Missing required dataset file '{filename}' at {file_path}"
                    logger.error(msg)
                    raise FileNotFoundError(msg)

                # 2. Read raw CSV
                df = pd.read_csv(file_path, dtype=str)

                # 3. Validate expected columns against schema
                missing_columns = [col for col in expected_columns if col not in df.columns]
                if missing_columns:
                    msg = (
                        f"Critical Schema Error: Dataset '{filename}' is missing expected columns: "
                        f"{missing_columns}. Found columns: {list(df.columns)}"
                    )
                    logger.error(msg)
                    raise ValueError(msg)

                # 4. Load into SQLite inside transaction
                with conn:
                    # Drop table to ensure idempotent recreation
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                    df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=25000)

                # 5. Verify row count
                cur = conn.cursor()
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                loaded_count = cur.fetchone()[0]
                row_counts[table_name] = loaded_count

                logger.info(f"Loaded {loaded_count:,d} rows into table '{table_name}' from '{filename}'")

                if loaded_count != len(df):
                    msg = f"Row count mismatch for {table_name}: CSV had {len(df)}, table has {loaded_count}"
                    logger.error(msg)
                    raise ValueError(msg)

    except Exception as exc:
        logger.error(f"Extract & Load aborted due to error: {exc}")
        conn.close()
        raise
    finally:
        conn.close()

    logger.info(f"Successfully loaded all {len(row_counts)} raw tables into SQLite.")
    return row_counts


if __name__ == "__main__":
    try:
        extract_and_load()
    except Exception as e:
        sys.exit(1)
