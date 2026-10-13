-- Query 5: Average Delivery Delay vs Estimated Date & Review Score Correlation
-- Requirements:
--   - Uses CTEs and window functions
--   - Delivered orders only
--   - Bucketed: ('early', 'on time', '1-3 days late', '4-7 days late', '8+ days late')
--   - Latest review per order to avoid survey double-counting
--   - Reports average delivery delay days, average review score, and % negative/positive ratings

WITH latest_reviews AS (
    SELECT
        order_id,
        review_score
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
),
delivered_delay_base AS (
    SELECT
        o.order_id,
        r.review_score,
        ROUND(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_estimated_delivery_date), 2) AS exact_delay_days,
        CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) AS day_delay,
        CASE
            WHEN DATE(o.order_delivered_customer_date) < DATE(o.order_estimated_delivery_date) THEN 'early'
            WHEN DATE(o.order_delivered_customer_date) = DATE(o.order_estimated_delivery_date) THEN 'on time'
            WHEN CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) BETWEEN 1 AND 3 THEN '1-3 days late'
            WHEN CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) BETWEEN 4 AND 7 THEN '4-7 days late'
            WHEN CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) >= 8 THEN '8+ days late'
            ELSE 'unknown'
        END AS delay_bucket,
        CASE
            WHEN DATE(o.order_delivered_customer_date) < DATE(o.order_estimated_delivery_date) THEN 1
            WHEN DATE(o.order_delivered_customer_date) = DATE(o.order_estimated_delivery_date) THEN 2
            WHEN CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) BETWEEN 1 AND 3 THEN 3
            WHEN CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) BETWEEN 4 AND 7 THEN 4
            WHEN CAST(ROUND(JULIANDAY(DATE(o.order_delivered_customer_date)) - JULIANDAY(DATE(o.order_estimated_delivery_date))) AS INTEGER) >= 8 THEN 5
            ELSE 6
        END AS bucket_sort_order
    FROM stg_orders o
    JOIN latest_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
)
SELECT
    delay_bucket,
    COUNT(*) AS delivered_orders_count,
    ROUND(AVG(exact_delay_days), 2) AS avg_delay_days,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(100.0 * SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_positive_reviews_4_5,
    ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_negative_reviews_1_2
FROM delivered_delay_base
GROUP BY delay_bucket, bucket_sort_order
ORDER BY bucket_sort_order ASC;
