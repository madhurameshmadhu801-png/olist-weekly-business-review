"""Main CLI orchestrator for executing the Olist ELT pipeline end-to-end."""
import argparse
import sys
import time
from pathlib import Path

from pipeline.config import DB_PATH
from pipeline.extract_load import extract_and_load
from pipeline.generate_reports import generate_all_reports
from pipeline.logging_setup import log_step, setup_logger
from pipeline.quality_checks import run_quality_checks
from pipeline.transform import transform_staging_and_marts

logger = setup_logger("run_pipeline")


def run_pipeline(
    db_path: Path = DB_PATH,
    include_reporting: bool = True,
) -> dict:
    """Executes the complete pipeline: Extract/Load -> Transform -> Quality Checks -> Reports/PDF."""
    start_time = time.time()
    logger.info("==================================================================")
    logger.info("       STARTING OLIST WEEKLY BUSINESS REVIEW DATA PIPELINE       ")
    logger.info("==================================================================")
    logger.info(f"Target SQLite Database: {db_path.resolve()}")

    summary = {
        "status": "FAILED",
        "raw_counts": {},
        "stg_mart_counts": {},
        "dq_status": "PENDING",
        "total_duration_sec": 0.0,
    }

    try:
        # Step 1: Extract & Load
        with log_step(logger, "PIPELINE STEP 1: Extract & Load (Raw Ingestion)"):
            raw_counts = extract_and_load(db_path=db_path)
            summary["raw_counts"] = raw_counts

        # Step 2: Transform Staging & Marts
        with log_step(logger, "PIPELINE STEP 2: Transform (Staging & Marts)"):
            stg_mart_counts = transform_staging_and_marts(db_path=db_path)
            summary["stg_mart_counts"] = stg_mart_counts

        # Step 3: Quality Checks
        with log_step(logger, "PIPELINE STEP 3: Data Quality Checks Suite"):
            dq_df = run_quality_checks(db_path=db_path)
            summary["dq_status"] = "PASSED"

        # Step 4: Analytical Reporting, Visualizations & Executive PDF
        if include_reporting:
            with log_step(logger, "PIPELINE STEP 4: Analytical SQL, Visualizations & PDF Report"):
                report_meta = generate_all_reports()
                summary["reports"] = report_meta

        total_duration = time.time() - start_time
        summary["total_duration_sec"] = round(total_duration, 2)
        summary["status"] = "SUCCESS"

        logger.info("==================================================================")
        logger.info(f"  PIPELINE EXECUTED SUCCESSFULLY IN {total_duration:.2f}s  ")
        logger.info("==================================================================")
        return summary

    except Exception as exc:
        total_duration = time.time() - start_time
        summary["total_duration_sec"] = round(total_duration, 2)
        logger.critical(f"FATAL: Pipeline execution halted with error: {exc}", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Olist Weekly Business Review ELT Pipeline")
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(DB_PATH),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--skip-reports",
        action="store_true",
        help="Skip Part C SQL analytics, chart rendering, and PDF generation",
    )
    args = parser.parse_args()

    try:
        run_pipeline(
            db_path=Path(args.db_path),
            include_reporting=not args.skip_reports,
        )
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
