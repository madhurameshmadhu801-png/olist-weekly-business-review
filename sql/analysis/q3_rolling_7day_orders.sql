-- Query 3: 7-Day Rolling Average of Daily Order Count
-- Requirements:
--   - Uses CTEs and window functions
--   - Zero-filled continuous calendar via recursive CTE to avoid gaps on zero-order days
--   - Rolling average computed with ROWS BETWEEN 6 PRECEDING AND CURRENT ROW

WITH RECURSIVE calendar(calendar_date) AS (
    SELECT MIN(DATE(purchase_date))
    FROM mart_orders
    WHERE purchase_date IS NOT NULL
    UNION ALL
    SELECT DATE(calendar_date, '+1 day')
    FROM calendar
    WHERE calendar_date < (SELECT MAX(DATE(purchase_date)) FROM mart_orders WHERE purchase_date IS NOT NULL)
),
daily_order_aggregates AS (
    SELECT
        DATE(purchase_date) AS order_date,
        COUNT(DISTINCT order_id) AS orders_count,
        ROUND(SUM(items_revenue), 2) AS daily_item_revenue
    FROM mart_orders
    WHERE purchase_date IS NOT NULL
    GROUP BY DATE(purchase_date)
),
zero_filled_daily_series AS (
    SELECT
        c.calendar_date AS order_date,
        COALESCE(d.orders_count, 0) AS daily_orders_count,
        COALESCE(d.daily_item_revenue, 0.0) AS daily_item_revenue
    FROM calendar c
    LEFT JOIN daily_order_aggregates d ON c.calendar_date = d.order_date
)
SELECT
    order_date,
    daily_orders_count,
    daily_item_revenue,
    ROUND(AVG(daily_orders_count) OVER (
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7day_avg_orders,
    ROUND(AVG(daily_item_revenue) OVER (
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7day_avg_revenue
FROM zero_filled_daily_series
ORDER BY order_date ASC;
