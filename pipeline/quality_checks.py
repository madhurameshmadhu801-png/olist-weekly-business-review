"""Data Quality execution engine running SQL checks and recording findings."""
import sqlite3
import sys
from pathlib import Path
import pandas as pd

from pipeline.config import DB_PATH, DQ_SUMMARY_PATH, REPORTS_DIR, SQL_QUALITY_DIR
from pipeline.logging_setup import log_step, setup_logger

logger = setup_logger("quality_checks")

# Definitions of checks with policies and documented reasons
CHECK_CONFIGS = [
    {
        "file": "check1_null_duplicate_orders.sql",
        "check_name": "Null or duplicate order_id in orders",
        "policy": "BLOCKING",
        "handling": "dropped/aborted",
        "reason": "Primary key uniqueness violation. Pipeline cannot proceed with corrupt order keys.",
    },
    {
        "file": "check2_delivered_before_purchase.sql",
        "check_name": "Delivered date earlier than purchase date",
        "policy": "FLAGGED",
        "handling": "flagged",
        "reason": "Logistics tracking system timestamp discrepancy; flagged in dq_flag for operational review.",
    },
    {
        "file": "check3_payment_item_freight_mismatch.sql",
        "check_name": "Payment total not matching item price + freight (> 0.01 tolerance)",
        "policy": "FLAGGED",
        "handling": "flagged",
        "reason": "Discrepancy caused by customer financing interest, voucher credits, or banking rounding.",
    },
    {
        "file": "check4_orders_missing_customer.sql",
        "check_name": "Orders with no matching customer record",
        "policy": "BLOCKING",
        "handling": "dropped/aborted",
        "reason": "Referential integrity failure. Every order must link to an identified customer.",
    },
    {
        "file": "check5_items_missing_foreign_keys.sql",
        "check_name": "Order items referencing missing orders, products or sellers",
        "policy": "BLOCKING",
        "handling": "dropped/aborted",
        "reason": "Orphan line items detected. Every line item must reference valid order, product, and seller.",
    },
    {
        "file": "check6_delivered_missing_delivered_date.sql",
        "check_name": "Delivered orders missing delivered date",
        "policy": "FLAGGED",
        "handling": "flagged",
        "reason": "Order marked delivered in status but carrier delivery timestamp is NULL.",
    },
    {
        "file": "check7_invalid_review_scores.sql",
        "check_name": "Review scores outside 1-5 or duplicate review_ids",
        "policy": "FLAGGED",
        "handling": "flagged",
        "reason": "Customer satisfaction survey integrity; duplicates flagged to prevent double counting.",
    },
]


def run_quality_checks(
    db_path: Path = DB_PATH,
    sql_quality_dir: Path = SQL_QUALITY_DIR,
    dq_summary_path: Path = DQ_SUMMARY_PATH,
) -> pd.DataFrame:
    """Executes all DQ SQL checks, updates dq_flag in mart_orders, and generates dq_summary.csv."""
    logger.info("Executing Data Quality checks suite...")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    summary_records = []
    blocking_failures = []

    try:
        for cfg in CHECK_CONFIGS:
            sql_file = sql_quality_dir / cfg["file"]
            check_name = cfg["check_name"]
            policy = cfg["policy"]
            handling = cfg["handling"]
            reason = cfg["reason"]

            if not sql_file.exists():
                raise FileNotFoundError(f"DQ check query file not found: {sql_file}")

            with open(sql_file, "r", encoding="utf-8") as f:
                query = f.read()

            with log_step(logger, f"Running DQ Check: {check_name} [{policy}]"):
                cur = conn.cursor()
                cur.execute(query)
                rows = cur.fetchall()
                rows_failing = len(rows)

                logger.info(
                    f"Check '{check_name}': {rows_failing} failing rows. Policy: {policy}. Handling: {handling}."
                )

                summary_records.append({
                    "check": check_name,
                    "rows_failing": rows_failing,
                    "handling": handling if rows_failing > 0 else "passed",
                    "reason": reason,
                })

                # Handle blocking failure
                if policy == "BLOCKING" and rows_failing > 0:
                    blocking_failures.append((check_name, rows_failing))

                # Handle flagged checks by updating dq_flag in mart_orders
                elif policy == "FLAGGED" and rows_failing > 0:
                    flag_code = cfg["file"].replace(".sql", "").upper()
                    # Check if query returned order_id as first column
                    order_ids = [r[0] for r in rows if r and r[0] is not None]
                    if order_ids:
                        with conn:
                            # Batch update in sqlite
                            placeholders = ",".join("?" for _ in order_ids)
                            update_sql = f"""
                                UPDATE mart_orders
                                SET dq_flag = CASE
                                    WHEN dq_flag IS NULL THEN ?
                                    ELSE dq_flag || ';' || ?
                                END
                                WHERE order_id IN ({placeholders})
                            """
                            cur.execute(update_sql, [flag_code, flag_code] + order_ids)
                        logger.info(f"Updated dq_flag with '{flag_code}' for {len(order_ids)} orders in mart_orders.")

        # Save dq_summary.csv
        summary_df = pd.DataFrame(summary_records)
        summary_df.to_csv(dq_summary_path, index=False)
        logger.info(f"Saved Data Quality summary report to '{dq_summary_path}'.")

        # Raise exception on blocking failures after evaluating all checks
        if blocking_failures:
            err_msg = f"Critical Data Quality Check Failures (Pipeline Halted): {blocking_failures}"
            logger.critical(err_msg)
            raise RuntimeError(err_msg)

    finally:
        conn.close()

    logger.info("All Data Quality checks completed successfully.")
    return summary_df


if __name__ == "__main__":
    try:
        run_quality_checks()
    except Exception:
        sys.exit(1)
