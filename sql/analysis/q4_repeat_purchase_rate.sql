-- Query 4: Repeat-Purchase Rate (Correct vs Incorrect Data Model Identification)
-- Requirements:
--   - Uses CTEs and window functions / aggregation
--   - Correct rate: computed using customer_unique_id
--   - Wrong rate: computed using customer_id
--
-- EXPLANATION OF DATA MODEL DIFFERENCE:
-- In Olist's schema architecture:
-- 1. `customer_id` is an order-scoped surrogate key generated per transaction.
--    Every order has a brand new customer_id assigned, meaning COUNT(DISTINCT customer_id)
--    almost matches COUNT(DISTINCT order_id). Using customer_id yields a false 0.00% repeat rate.
-- 2. `customer_unique_id` is the actual permanent customer identity hash across multiple visits.
--    Using customer_unique_id correctly reveals returning buyers who placed 2+ orders.

WITH correct_unique_customers AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS orders_placed
    FROM mart_orders
    WHERE customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
),
correct_summary AS (
    SELECT
        'customer_unique_id (CORRECT: permanent user identity)' AS identification_method,
        COUNT(*) AS total_customers,
        SUM(CASE WHEN orders_placed >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
        SUM(CASE WHEN orders_placed = 1 THEN 1 ELSE 0 END) AS single_order_customers,
        ROUND(100.0 * SUM(CASE WHEN orders_placed >= 2 THEN 1 ELSE 0 END) / COUNT(*), 4) AS repeat_purchase_rate_pct
    FROM correct_unique_customers
),
wrong_customer_id AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS orders_placed
    FROM mart_orders
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
wrong_summary AS (
    SELECT
        'customer_id (INCORRECT: order-scoped surrogate key)' AS identification_method,
        COUNT(*) AS total_customers,
        SUM(CASE WHEN orders_placed >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
        SUM(CASE WHEN orders_placed = 1 THEN 1 ELSE 0 END) AS single_order_customers,
        ROUND(100.0 * SUM(CASE WHEN orders_placed >= 2 THEN 1 ELSE 0 END) / COUNT(*), 4) AS repeat_purchase_rate_pct
    FROM wrong_customer_id
)
SELECT * FROM correct_summary
UNION ALL
SELECT * FROM wrong_summary;
