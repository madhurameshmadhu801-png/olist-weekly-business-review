-- Query 1: Month-over-Month Revenue and Growth %
-- Requirements:
--   - Uses CTEs and window function LAG()
--   - Filters for delivered orders only
--   - Computes both Item Revenue (excluding freight) and Total Marketplace GMV (including freight)
--   - Flags edge months (2016 launch ramp and 2018 cutoff) where data collection was partial
-- Freight Policy:
--   - Item Revenue represents merchant merchandise value.
--   - Freight Total represents logistics revenue paid by consumers.
--   - Both metrics and their respective MoM growth percentages are reported side-by-side.

WITH monthly_orders AS (
    SELECT
        STRFTIME('%Y-%m', purchase_date) AS order_month,
        COUNT(DISTINCT order_id) AS delivered_orders_count,
        ROUND(SUM(items_revenue), 2) AS item_revenue_excl_freight,
        ROUND(SUM(freight_total), 2) AS freight_revenue,
        ROUND(SUM(items_revenue + freight_total), 2) AS total_gmv_incl_freight
    FROM mart_orders
    WHERE order_status = 'delivered'
      AND purchase_date IS NOT NULL
    GROUP BY STRFTIME('%Y-%m', purchase_date)
),
mom_lagged AS (
    SELECT
        order_month,
        delivered_orders_count,
        item_revenue_excl_freight,
        freight_revenue,
        total_gmv_incl_freight,
        LAG(item_revenue_excl_freight, 1) OVER (ORDER BY order_month) AS prev_month_item_rev,
        LAG(total_gmv_incl_freight, 1) OVER (ORDER BY order_month) AS prev_month_total_gmv,
        CASE
            WHEN order_month IN ('2016-09', '2016-10', '2016-12') THEN 'INCOMPLETE_LAUNCH_EDGE'
            ELSE 'COMPLETE_OPERATIONAL_MONTH'
        END AS month_completeness_flag
    FROM monthly_orders
)
SELECT
    order_month,
    month_completeness_flag,
    delivered_orders_count,
    item_revenue_excl_freight,
    prev_month_item_rev,
    CASE
        WHEN prev_month_item_rev IS NULL OR prev_month_item_rev = 0 THEN NULL
        ELSE ROUND(100.0 * (item_revenue_excl_freight - prev_month_item_rev) / prev_month_item_rev, 2)
    END AS mom_item_revenue_growth_pct,
    total_gmv_incl_freight,
    prev_month_total_gmv,
    CASE
        WHEN prev_month_total_gmv IS NULL OR prev_month_total_gmv = 0 THEN NULL
        ELSE ROUND(100.0 * (total_gmv_incl_freight - prev_month_total_gmv) / prev_month_total_gmv, 2)
    END AS mom_total_gmv_growth_pct
FROM mom_lagged
ORDER BY order_month ASC;
