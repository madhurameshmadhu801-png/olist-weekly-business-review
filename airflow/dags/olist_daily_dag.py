"""Airflow DAG for daily execution of the Olist E-commerce ELT Pipeline."""
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure pipeline root is in python search path
DAG_DIR = Path(__file__).resolve().parent
REPO_ROOT = DAG_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from airflow import DAG
from airflow.operators.python import PythonOperator

from pipeline.extract_load import extract_and_load
from pipeline.generate_reports import generate_all_reports
from pipeline.quality_checks import run_quality_checks
from pipeline.transform import transform_staging_and_marts


def run_extract_load_task(**kwargs):
    """Airflow callable for extracting raw CSVs and loading verbatim into raw_* tables."""
    return extract_and_load()


def run_transform_task(**kwargs):
    """Airflow callable for building cleaned stg_* staging tables."""
    return transform_staging_and_marts()


def run_quality_checks_task(**kwargs):
    """Airflow callable for running SQL DQ checks and writing dq_summary.csv."""
    df = run_quality_checks()
    return {"status": "PASSED", "checks_run": len(df)}


def run_build_marts_and_reports_task(**kwargs):
    """Airflow callable for compiling marts, running analytical queries, charts, and PDF report."""
    return generate_all_reports()


default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="olist_daily_wbreview_pipeline",
    default_args=default_args,
    description="Daily ELT pipeline & WBR reporting for Olist E-Commerce Marketplace",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "olist", "wbr", "elt", "data_quality"],
) as dag:

    task_extract_load = PythonOperator(
        task_id="extract_load",
        python_callable=run_extract_load_task,
    )

    task_transform = PythonOperator(
        task_id="transform",
        python_callable=run_transform_task,
    )

    task_quality_checks = PythonOperator(
        task_id="quality_checks",
        python_callable=run_quality_checks_task,
    )

    task_build_marts = PythonOperator(
        task_id="build_marts",
        python_callable=run_build_marts_and_reports_task,
    )

    # Task dependency graph:
    # extract_load >> transform >> quality_checks >> build_marts
    task_extract_load >> task_transform >> task_quality_checks >> task_build_marts
