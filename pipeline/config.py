"""Configuration settings, paths, schema definitions, and table mappings."""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = BASE_DIR / "olist.db"

# Logs & Reports
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "pipeline.log"
REPORTS_DIR = BASE_DIR / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"
RESULTS_DIR = REPORTS_DIR / "results"
DQ_SUMMARY_PATH = REPORTS_DIR / "dq_summary.csv"
FINAL_PDF_PATH = REPORTS_DIR / "Olist_Weekly_Business_Review.pdf"

# SQL Directory Paths
SQL_DIR = BASE_DIR / "sql"
SQL_QUALITY_DIR = SQL_DIR / "quality"
SQL_ANALYSIS_DIR = SQL_DIR / "analysis"

# Tolerances & Thresholds
PAYMENT_TOLERANCE = 0.01

# Expected Raw CSV Schema Mapping
RAW_TABLE_SCHEMAS = {
    "olist_customers_dataset.csv": {
        "table": "raw_customers",
        "expected_columns": [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    },
    "olist_geolocation_dataset.csv": {
        "table": "raw_geolocation",
        "expected_columns": [
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ],
    },
    "olist_order_items_dataset.csv": {
        "table": "raw_order_items",
        "expected_columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    },
    "olist_order_payments_dataset.csv": {
        "table": "raw_order_payments",
        "expected_columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    },
    "olist_order_reviews_dataset.csv": {
        "table": "raw_order_reviews",
        "expected_columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    },
    "olist_orders_dataset.csv": {
        "table": "raw_orders",
        "expected_columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    "olist_products_dataset.csv": {
        "table": "raw_products",
        "expected_columns": [
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    },
    "olist_sellers_dataset.csv": {
        "table": "raw_sellers",
        "expected_columns": [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ],
    },
    "product_category_name_translation.csv": {
        "table": "raw_product_category_name_translation",
        "expected_columns": [
            "product_category_name",
            "product_category_name_english",
        ],
    },
}

# Staging Tables
STG_TABLES = [
    "stg_customers",
    "stg_geolocation",
    "stg_orders",
    "stg_order_items",
    "stg_order_payments",
    "stg_order_reviews",
    "stg_products",
    "stg_sellers",
]

# Mart Tables
MART_TABLES = [
    "mart_orders",
    "mart_order_items_enriched",
]
