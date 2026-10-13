-- Query 2: Top 3 Product Categories Per Customer State by Revenue
-- Requirements:
--   - Uses CTEs and window function DENSE_RANK()
--   - English category names translated from Portuguese
--   - Filters for delivered orders to evaluate realized customer revenue
--   - Groups by customer state and category, avoiding join double-counting

WITH state_category_sales AS (
    SELECT
        customer_state,
        product_category_name_english AS category_name,
        ROUND(SUM(price), 2) AS category_revenue,
        COUNT(*) AS items_purchased,
        COUNT(DISTINCT order_id) AS distinct_orders_count
    FROM mart_order_items_enriched
    WHERE order_status = 'delivered'
      AND customer_state IS NOT NULL
      AND product_category_name_english IS NOT NULL
      AND product_category_name_english != 'unknown'
    GROUP BY customer_state, product_category_name_english
),
ranked_categories AS (
    SELECT
        customer_state,
        category_name,
        category_revenue,
        items_purchased,
        distinct_orders_count,
        DENSE_RANK() OVER (
            PARTITION BY customer_state
            ORDER BY category_revenue DESC
        ) AS rank_by_revenue
    FROM state_category_sales
)
SELECT
    customer_state,
    rank_by_revenue,
    category_name,
    category_revenue,
    items_purchased,
    distinct_orders_count
FROM ranked_categories
WHERE rank_by_revenue <= 3
ORDER BY customer_state ASC, rank_by_revenue ASC;
