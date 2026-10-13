"""Transform raw tables into cleaned staging tables and analysis-ready data marts."""
import sqlite3
import sys
from pathlib import Path

from pipeline.config import DB_PATH
from pipeline.logging_setup import log_step, setup_logger

logger = setup_logger("transform")


def transform_staging_and_marts(db_path: Path = DB_PATH) -> dict[str, int]:
    """Builds cleaned staging tables and analysis-ready marts idempotently inside transactions."""
    logger.info("Starting staging and marts transformation...")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    table_counts = {}

    try:
        # ==========================================
        # 1. BUILD STAGING TABLES
        # ==========================================
        with log_step(logger, "Building stg_customers"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_customers;")
                conn.execute("""
                    CREATE TABLE stg_customers AS
                    SELECT DISTINCT
                        TRIM(customer_id) AS customer_id,
                        TRIM(customer_unique_id) AS customer_unique_id,
                        CAST(customer_zip_code_prefix AS INTEGER) AS customer_zip_code_prefix,
                        LOWER(TRIM(customer_city)) AS customer_city,
                        UPPER(TRIM(customer_state)) AS customer_state
                    FROM raw_customers
                    WHERE customer_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_customers_id ON stg_customers(customer_id);")
                conn.execute("CREATE INDEX idx_stg_customers_uniq ON stg_customers(customer_unique_id);")

        with log_step(logger, "Building stg_geolocation"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_geolocation;")
                conn.execute("""
                    CREATE TABLE stg_geolocation AS
                    SELECT
                        CAST(geolocation_zip_code_prefix AS INTEGER) AS geolocation_zip_code_prefix,
                        AVG(CAST(geolocation_lat AS REAL)) AS geolocation_lat,
                        AVG(CAST(geolocation_lng AS REAL)) AS geolocation_lng,
                        LOWER(TRIM(geolocation_city)) AS geolocation_city,
                        UPPER(TRIM(geolocation_state)) AS geolocation_state
                    FROM raw_geolocation
                    WHERE geolocation_zip_code_prefix IS NOT NULL
                    GROUP BY geolocation_zip_code_prefix, UPPER(TRIM(geolocation_state));
                """)
                conn.execute("CREATE INDEX idx_stg_geo_zip ON stg_geolocation(geolocation_zip_code_prefix);")

        with log_step(logger, "Building stg_orders"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_orders;")
                conn.execute("""
                    CREATE TABLE stg_orders AS
                    SELECT DISTINCT
                        TRIM(order_id) AS order_id,
                        TRIM(customer_id) AS customer_id,
                        LOWER(TRIM(order_status)) AS order_status,
                        TRIM(order_purchase_timestamp) AS order_purchase_timestamp,
                        CASE WHEN order_approved_at IN ('', 'null', 'None') THEN NULL ELSE TRIM(order_approved_at) END AS order_approved_at,
                        CASE WHEN order_delivered_carrier_date IN ('', 'null', 'None') THEN NULL ELSE TRIM(order_delivered_carrier_date) END AS order_delivered_carrier_date,
                        CASE WHEN order_delivered_customer_date IN ('', 'null', 'None') THEN NULL ELSE TRIM(order_delivered_customer_date) END AS order_delivered_customer_date,
                        CASE WHEN order_estimated_delivery_date IN ('', 'null', 'None') THEN NULL ELSE TRIM(order_estimated_delivery_date) END AS order_estimated_delivery_date
                    FROM raw_orders
                    WHERE order_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_orders_id ON stg_orders(order_id);")
                conn.execute("CREATE INDEX idx_stg_orders_cust ON stg_orders(customer_id);")

        with log_step(logger, "Building stg_order_items"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_order_items;")
                conn.execute("""
                    CREATE TABLE stg_order_items AS
                    SELECT DISTINCT
                        TRIM(order_id) AS order_id,
                        CAST(order_item_id AS INTEGER) AS order_item_id,
                        TRIM(product_id) AS product_id,
                        TRIM(seller_id) AS seller_id,
                        TRIM(shipping_limit_date) AS shipping_limit_date,
                        CAST(price AS REAL) AS price,
                        CAST(freight_value AS REAL) AS freight_value
                    FROM raw_order_items
                    WHERE order_id IS NOT NULL AND order_item_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_items_order ON stg_order_items(order_id);")
                conn.execute("CREATE INDEX idx_stg_items_prod ON stg_order_items(product_id);")
                conn.execute("CREATE INDEX idx_stg_items_seller ON stg_order_items(seller_id);")

        with log_step(logger, "Building stg_order_payments"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_order_payments;")
                conn.execute("""
                    CREATE TABLE stg_order_payments AS
                    SELECT
                        TRIM(order_id) AS order_id,
                        CAST(payment_sequential AS INTEGER) AS payment_sequential,
                        LOWER(TRIM(payment_type)) AS payment_type,
                        CAST(payment_installments AS INTEGER) AS payment_installments,
                        CAST(payment_value AS REAL) AS payment_value
                    FROM raw_order_payments
                    WHERE order_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_pmt_order ON stg_order_payments(order_id);")

        with log_step(logger, "Building stg_order_reviews"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_order_reviews;")
                conn.execute("""
                    CREATE TABLE stg_order_reviews AS
                    SELECT DISTINCT
                        TRIM(review_id) AS review_id,
                        TRIM(order_id) AS order_id,
                        CAST(review_score AS INTEGER) AS review_score,
                        CASE WHEN review_comment_title IN ('', 'null', 'None') THEN NULL ELSE TRIM(review_comment_title) END AS review_comment_title,
                        CASE WHEN review_comment_message IN ('', 'null', 'None') THEN NULL ELSE TRIM(review_comment_message) END AS review_comment_message,
                        TRIM(review_creation_date) AS review_creation_date,
                        TRIM(review_answer_timestamp) AS review_answer_timestamp
                    FROM raw_order_reviews
                    WHERE review_id IS NOT NULL AND order_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_rev_order ON stg_order_reviews(order_id);")

        with log_step(logger, "Building stg_products"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_products;")
                conn.execute("""
                    CREATE TABLE stg_products AS
                    SELECT DISTINCT
                        TRIM(p.product_id) AS product_id,
                        TRIM(p.product_category_name) AS product_category_name,
                        COALESCE(
                            TRIM(t.product_category_name_english),
                            TRIM(p.product_category_name),
                            'unknown'
                        ) AS product_category_name_english,
                        CAST(p.product_name_lenght AS INTEGER) AS product_name_length,
                        CAST(p.product_description_lenght AS INTEGER) AS product_description_length,
                        CAST(p.product_photos_qty AS INTEGER) AS product_photos_qty,
                        CAST(p.product_weight_g AS REAL) AS product_weight_g,
                        CAST(p.product_length_cm AS REAL) AS product_length_cm,
                        CAST(p.product_height_cm AS REAL) AS product_height_cm,
                        CAST(p.product_width_cm AS REAL) AS product_width_cm
                    FROM raw_products p
                    LEFT JOIN raw_product_category_name_translation t
                        ON TRIM(p.product_category_name) = TRIM(t.product_category_name)
                    WHERE p.product_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_prod_id ON stg_products(product_id);")

        with log_step(logger, "Building stg_sellers"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS stg_sellers;")
                conn.execute("""
                    CREATE TABLE stg_sellers AS
                    SELECT DISTINCT
                        TRIM(seller_id) AS seller_id,
                        CAST(seller_zip_code_prefix AS INTEGER) AS seller_zip_code_prefix,
                        LOWER(TRIM(seller_city)) AS seller_city,
                        UPPER(TRIM(seller_state)) AS seller_state
                    FROM raw_sellers
                    WHERE seller_id IS NOT NULL;
                """)
                conn.execute("CREATE INDEX idx_stg_seller_id ON stg_sellers(seller_id);")

        # ==========================================
        # 2. BUILD MARTS
        # ==========================================
        with log_step(logger, "Building mart_orders"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS mart_orders;")
                conn.execute("""
                    CREATE TABLE mart_orders AS
                    WITH items_agg AS (
                        SELECT
                            order_id,
                            COUNT(*) AS item_count,
                            ROUND(SUM(price), 2) AS items_revenue,
                            ROUND(SUM(freight_value), 2) AS freight_total
                        FROM stg_order_items
                        GROUP BY order_id
                    ),
                    payments_agg AS (
                        SELECT
                            order_id,
                            ROUND(SUM(payment_value), 2) AS payments_total
                        FROM stg_order_payments
                        GROUP BY order_id
                    ),
                    reviews_latest AS (
                        SELECT order_id, review_score
                        FROM (
                            SELECT
                                order_id,
                                review_score,
                                ROW_NUMBER() OVER (
                                    PARTITION BY order_id
                                    ORDER BY review_answer_timestamp DESC, review_creation_date DESC
                                ) AS rn
                            FROM stg_order_reviews
                        )
                        WHERE rn = 1
                    )
                    SELECT
                        o.order_id,
                        o.customer_id,
                        c.customer_unique_id,
                        c.customer_state,
                        o.order_status,
                        o.order_purchase_timestamp AS purchase_date,
                        o.order_approved_at AS approved_date,
                        o.order_delivered_carrier_date AS carrier_date,
                        o.order_delivered_customer_date AS delivered_date,
                        o.order_estimated_delivery_date AS estimated_date,
                        CASE
                            WHEN o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
                            THEN ROUND(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_estimated_delivery_date), 2)
                            ELSE NULL
                        END AS delivery_delay_days,
                        COALESCE(i.item_count, 0) AS item_count,
                        COALESCE(i.items_revenue, 0.0) AS items_revenue,
                        COALESCE(i.freight_total, 0.0) AS freight_total,
                        COALESCE(p.payments_total, 0.0) AS payments_total,
                        r.review_score,
                        CAST(NULL AS TEXT) AS dq_flag
                    FROM stg_orders o
                    LEFT JOIN stg_customers c ON o.customer_id = c.customer_id
                    LEFT JOIN items_agg i ON o.order_id = i.order_id
                    LEFT JOIN payments_agg p ON o.order_id = p.order_id
                    LEFT JOIN reviews_latest r ON o.order_id = r.order_id;
                """)
                conn.execute("CREATE UNIQUE INDEX idx_mart_orders_id ON mart_orders(order_id);")
                conn.execute("CREATE INDEX idx_mart_orders_cust_uniq ON mart_orders(customer_unique_id);")
                conn.execute("CREATE INDEX idx_mart_orders_status ON mart_orders(order_status);")
                conn.execute("CREATE INDEX idx_mart_orders_purchase ON mart_orders(purchase_date);")

        with log_step(logger, "Building mart_order_items_enriched"):
            with conn:
                conn.execute("DROP TABLE IF EXISTS mart_order_items_enriched;")
                conn.execute("""
                    CREATE TABLE mart_order_items_enriched AS
                    SELECT
                        i.order_id,
                        i.order_item_id,
                        i.product_id,
                        i.seller_id,
                        p.product_category_name_english,
                        i.price,
                        i.freight_value,
                        s.seller_state,
                        c.customer_state,
                        o.order_purchase_timestamp AS purchase_date,
                        o.order_status
                    FROM stg_order_items i
                    JOIN stg_orders o ON i.order_id = o.order_id
                    LEFT JOIN stg_customers c ON o.customer_id = c.customer_id
                    LEFT JOIN stg_products p ON i.product_id = p.product_id
                    LEFT JOIN stg_sellers s ON i.seller_id = s.seller_id;
                """)
                conn.execute("CREATE INDEX idx_mart_items_order ON mart_order_items_enriched(order_id);")
                conn.execute("CREATE INDEX idx_mart_items_cat ON mart_order_items_enriched(product_category_name_english);")
                conn.execute("CREATE INDEX idx_mart_items_seller_st ON mart_order_items_enriched(seller_state);")
                conn.execute("CREATE INDEX idx_mart_items_cust_st ON mart_order_items_enriched(customer_state);")

        # Collect summary counts
        tables_to_count = [
            "stg_customers",
            "stg_geolocation",
            "stg_orders",
            "stg_order_items",
            "stg_order_payments",
            "stg_order_reviews",
            "stg_products",
            "stg_sellers",
            "mart_orders",
            "mart_order_items_enriched",
        ]
        cur = conn.cursor()
        for tbl in tables_to_count:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            cnt = cur.fetchone()[0]
            table_counts[tbl] = cnt
            logger.info(f"Table '{tbl}' successfully created with {cnt:,d} rows.")

    finally:
        conn.close()

    logger.info("Staging and marts transformations completed successfully.")
    return table_counts


if __name__ == "__main__":
    try:
        transform_staging_and_marts()
    except Exception:
        sys.exit(1)
