# Weekly Business Review for an E-Commerce Marketplace (Olist)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![SQLite](https://img.shields.io/badge/database-SQLite-lightgrey.svg)](https://www.sqlite.org/)
[![Code Style: Clean & Modular](https://img.shields.io/badge/code%20style-modular%20ELT-success.svg)](#)

A production-grade, autonomous Data Engineering and Analytics project building an end-to-end ELT pipeline, automated data quality verification suite, pure-SQL analytical queries, KPI visual dashboards, and an executive 5-page PDF report for the **Olist Brazilian E-Commerce Public Dataset** (Kaggle: `olistbr/brazilian-ecommerce`).

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Environment Setup](#environment-setup)
4. [Dataset Download & Placement](#dataset-download--placement)
5. [Running the Pipeline](#running-the-pipeline)
6. [Data Quality Suite (Part B)](#data-quality-suite-part-b)
7. [Analytical SQL Suite (Part C)](#analytical-sql-suite-part-c)
8. [Executive Report & Metrics (Part D)](#executive-report--metrics-part-d)
9. [Running Tests (Idempotency)](#running-tests-idempotency)
10. [Airflow DAG Orchestration](#airflow-dag-orchestration)
11. [Key Assumptions](#key-assumptions)
12. [AI Assistance Disclosure](#ai-assistance-disclosure)

---

## 1. Project Overview

The objective of this project is two-fold:
1. **Trustworthy Weekly Metrics Pipeline:** Ingest 9 raw CSV datasets (~100k orders, 1M geolocation records), perform schema validation, apply staging transformations (type casting, timestamp parsing, text normalization, and English category translation), and build analysis-ready marts (`mart_orders`, `mart_order_items_enriched`) with zero Cartesian fan-out and guaranteed idempotency.
2. **Data-Backed Executive Recommendation:** Investigate what hurts customer satisfaction, verify the delivery delay hypothesis, evaluate regional logistics bottlenecks, and deliver an actionable 1-page memo to leadership.

---

## 2. Repository Structure

```
olist-weekly-business-review/
├── pipeline/                              # Core ELT & Python execution modules
│   ├── __init__.py
│   ├── config.py                          # Path definitions, raw schemas, tolerances
│   ├── logging_setup.py                   # Structured console & file logging (logs/pipeline.log)
│   ├── extract_load.py                    # Schema validation and verbatim raw ingestion
│   ├── transform.py                       # Staging tables & marts transformation
│   ├── quality_checks.py                  # SQL DQ engine & dq_summary.csv writer
│   ├── generate_reports.py                # SQL query runner, chart generator & ReportLab PDF compiler
│   └── run_pipeline.py                    # Main CLI entrypoint
├── sql/
│   ├── quality/                           # Standalone SQL quality check queries
│   │   ├── check1_null_duplicate_orders.sql
│   │   ├── check2_delivered_before_purchase.sql
│   │   ├── check3_payment_item_freight_mismatch.sql
│   │   ├── check4_orders_missing_customer.sql
│   │   ├── check5_items_missing_foreign_keys.sql
│   │   ├── check6_delivered_missing_delivered_date.sql
│   │   └── check7_invalid_review_scores.sql
│   └── analysis/                          # Pure SQL CTE & window function analytical queries
│       ├── q1_mom_revenue.sql             # MoM revenue and growth % using LAG()
│       ├── q2_top3_categories_by_state.sql# Top 3 categories per state using DENSE_RANK()
│       ├── q3_rolling_7day_orders.sql     # 7-day rolling order average via recursive calendar CTE
│       ├── q4_repeat_purchase_rate.sql    # Correct (customer_unique_id) vs incorrect repeat rates
│       └── q5_delivery_delay_vs_review.sql# Delivery delay buckets vs customer review scores
├── airflow/
│   └── dags/
│       └── olist_daily_dag.py             # Airflow DAG scheduled @daily (extract >> transform >> dq >> marts)
├── tests/
│   ├── __init__.py
│   └── test_idempotency.py                # Double-run test asserting identical row counts
├── reports/                               # Generated deliverables
│   ├── charts/                            # High-resolution PNG charts
│   ├── results/                           # Query results archive CSVs
│   ├── dq_summary.csv                     # Data quality findings summary
│   └── olist_weekly_business_review.pdf   # 5-Page Executive PDF Report
├── data/
│   └── raw/                               # Raw CSV datasets (git-ignored)
├── requirements.txt                       # Pinned Python dependencies
├── .gitignore                             # Excludes raw data, databases, logs, virtual environments
└── README.md
```

---

## 3. Environment Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- SQLite3 (included in standard library)
- Git & GitHub CLI (optional for cloning/publishing)

### Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/madhurameshmadhu801-png/olist-weekly-business-review.git
cd olist-weekly-business-review

# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install pinned requirements
pip install -r requirements.txt
```

---

## 4. Dataset Download & Placement

The dataset is the **Brazilian E-Commerce Public Dataset by Olist** on Kaggle:
```bash
# Automated download via Kaggle CLI:
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
```

If Kaggle API credentials are not configured, download the ZIP archive manually from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and extract the 9 CSV files into `data/raw/`:
1. `olist_customers_dataset.csv`
2. `olist_geolocation_dataset.csv`
3. `olist_orders_dataset.csv`
4. `olist_order_items_dataset.csv`
5. `olist_order_payments_dataset.csv`
6. `olist_order_reviews_dataset.csv`
7. `olist_products_dataset.csv`
8. `olist_sellers_dataset.csv`
9. `product_category_name_translation.csv`

---

## 5. Running the Pipeline

Execute the complete end-to-end pipeline (Raw Ingestion $\to$ Staging/Marts $\to$ Data Quality $\to$ SQL Analytics $\to$ Charts $\to$ PDF Report):

```bash
python -m pipeline.run_pipeline
```

### CLI Options:
```bash
# Run with custom SQLite database path:
python -m pipeline.run_pipeline --db-path my_custom_olist.db

# Run ELT and Data Quality checks only (skip charts and PDF generation):
python -m pipeline.run_pipeline --skip-reports
```

All execution steps, duration timers, and row counts are logged simultaneously to the console and to `logs/pipeline.log`.

---

## 6. Data Quality Suite (Part B)

Run the data quality suite independently:
```bash
python -m pipeline.quality_checks
```

The suite executes each query in `sql/quality/` and outputs `reports/dq_summary.csv`:

| Check | Policy | Rows Failing | Handling | Documented Reason |
| :--- | :---: | :---: | :---: | :--- |
| **Check 1:** Null or duplicate order_id | `BLOCKING` | 0 | passed | Primary key uniqueness violation; halts pipeline if violated. |
| **Check 2:** Delivered date earlier than purchase date | `FLAGGED` | 0 | passed | Anomaly in date logging; flagged in `dq_flag`. |
| **Check 3:** Payment total not matching item price + freight | `FLAGGED` | 375 | flagged | Credit card installment interest, voucher subsidies, and banking rounding. |
| **Check 4:** Orders with no matching customer record | `BLOCKING` | 0 | passed | Referential integrity constraint; halts pipeline on orphan orders. |
| **Check 5:** Items referencing missing orders/products/sellers | `BLOCKING` | 0 | passed | Referential integrity constraint; halts pipeline on orphan line items. |
| **Check 6:** Delivered orders missing delivered timestamp | `FLAGGED` | 8 | flagged | Carrier tracking status delivered but timestamp is NULL. |
| **Check 7:** Review scores outside 1-5 or duplicate review_ids | `FLAGGED` | 1,603 | flagged | Multiple survey submissions; pipeline joins latest review per order. |

Critical failures (`BLOCKING`) raise an exception and halt the pipeline. Documented dataset quirks (`FLAGGED`) update the `dq_flag` column on affected rows in `mart_orders` and allow downstream processing to complete.

---

## 7. Analytical SQL Suite (Part C)

Execute the analytical queries and export results to CSV:
```bash
python -m pipeline.generate_reports
```

All 5 analytical queries are written in **pure SQL (CTEs and window functions only)** with zero pandas data manipulation:

1. **`sql/analysis/q1_mom_revenue.sql` $\to$ `reports/q1_mom_revenue.csv`:**
   Computes monthly item revenue, freight total, total GMV, and month-over-month growth % using `LAG()`. Flags incomplete launch months (2016-09, 2016-10, 2016-12).
2. **`sql/analysis/q2_top3_categories_by_state.sql` $\to$ `reports/q2_top3_categories_by_state.csv`:**
   Identifies the top 3 product categories by revenue in each of the 27 Brazilian states using `DENSE_RANK()` and English category translations.
3. **`sql/analysis/q3_rolling_7day_orders.sql` $\to$ `reports/q3_rolling_7day_orders.csv`:**
   Generates a continuous zero-filled calendar using a recursive CTE and computes the 7-day rolling order average using `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`.
4. **`sql/analysis/q4_repeat_purchase_rate.sql` $\to$ `reports/q4_repeat_purchase_rate.csv`:**
   Compares the **correct repeat-purchase rate** using `customer_unique_id` (**3.12%**, 2,997 returning buyers out of 96,096 unique customers) against the **incorrect rate** using `customer_id` (**0.00%**, since `customer_id` is an order-scoped surrogate token generated per purchase).
5. **`sql/analysis/q5_delivery_delay_vs_review.sql` $\to$ `reports/q5_delivery_delay_vs_review.csv`:**
   Groups delivered orders into delay buckets (`early`, `on time`, `1-3 days late`, `4-7 days late`, `8+ days late`), using the latest review per order to avoid double-counting.

---

## 8. Executive Report & Metrics (Part D)

### Strategic Metrics Architecture
- **North Star Metric:** **Perfect Order Delivery Rate** = **77.15%**
  - *Formula:* `% of delivered orders that are on-time AND rated 4+ stars`
  - *Business Value:* Unified measure of operational logistics compliance and customer satisfaction.
- **Supporting Metrics:**
  - *On-Time Delivery Rate:* **93.34%** (`delivered_date <= estimated_date`)
  - *Average Review Score:* **4.16 / 5.0**
  - *Repeat-Purchase Rate:* **3.12%** (`customers with 2+ orders / total distinct customers`)
  - *Average Order Value (AOV):* **R$ 136.80** (Merchandise) / **R$ 159.56** (GMV with freight)
- **Guardrail Metric:**
  - *Customer Dissatisfaction Rate:* **12.81%** (`% of orders rated 1-2 stars`)

### Generated Charts
Saved to `reports/charts/` and `reports/`:
- `chart_mom_revenue.png`: Monthly GMV trajectory and MoM growth rate.
- `chart_delay_vs_review.png`: Review score collapse across delivery delay buckets.
- `chart_rolling_orders.png`: 7-day rolling daily order volume highlighting seasonal spikes (e.g., Black Friday 2017).
- `chart_late_delivery_by_state.png`: Regional logistics late delivery rates by state.

### Executive 5-Page PDF Report
Located at `reports/olist_weekly_business_review.pdf`:
- **Page 1:** Executive Summary, Metrics Hierarchy & High-Level KPIs.
- **Page 2:** One-Page Memo to Vice President (Root cause evidence, economic cost of churn, and the 48-Hour Seller SLA & Dynamic Buffering recommendation).
- **Page 3:** Data Quality Audit Table (`dq_summary.csv`) and technical analysis of quirks.
- **Page 4:** SQL Analytical deep-dive tables (MoM revenue, repeat rate comparison, top categories).
- **Page 5:** Visual 4-quadrant charts dashboard and forward operational roadmap.
- *Page Count Guarantee:* Verified strictly $\le 5$ pages via programmatic `pypdf` test.

---

## 9. Running Tests (Idempotency)

The idempotency test runs the pipeline twice sequentially on a test database and verifies that table row counts and primary keys remain perfectly identical:

```bash
python -m unittest tests/test_idempotency.py
```

Expected output:
```text
Ran 1 test in ~38s
OK
```

---

## 10. Airflow DAG Orchestration

The Airflow DAG is located at `airflow/dags/olist_daily_dag.py`:
- **DAG ID:** `olist_daily_wbreview_pipeline`
- **Schedule:** `@daily`
- **Task Pipeline:**
  $$\text{extract\_load} \longrightarrow \text{transform} \longrightarrow \text{quality\_checks} \longrightarrow \text{build\_marts}$$
- **Execution:** Uses `PythonOperator` calling core pipeline functions directly.

To deploy, copy or symlink `airflow/dags/olist_daily_dag.py` into your Airflow `$AIRFLOW_HOME/dags/` folder.

---

## 11. Key Assumptions

1. **Delivered Orders for Revenue & Delivery Analytics:** Canceled, unavailable, and in-transit orders are excluded from realized revenue and delay analytics because no final delivery occurred.
2. **Freight Separation:** Merchandise revenue and freight fees are tracked independently. Both are reported in MoM analysis to provide full transparency on seller take-rate vs carrier logistics costs.
3. **Latest Review Deduplication:** In instances where multiple reviews exist for a single `order_id`, the review with the latest `review_answer_timestamp` is used to represent the customer's final assessment.
4. **Calendar Generation:** A zero-filled continuous date series (via SQLite recursive CTE) is used for rolling calculations to avoid distortion from days with zero orders (e.g., early 2016).
5. **Installment Interest Handling:** Variances between `payment_value` and `price + freight` (375 orders) are recognized as banking interest fees and promotional vouchers, and are flagged rather than dropped.

---

## 12. AI Assistance Disclosure

In accordance with academic and professional integrity standards:
*An AI coding assistant was used to support code scaffolding, data quality query structuring, and documentation drafting during this project. All SQL queries, data models, business logic, metric definitions, and executive recommendations were thoroughly reviewed, validated against dataset documentation, and tested end-to-end by the author.*
