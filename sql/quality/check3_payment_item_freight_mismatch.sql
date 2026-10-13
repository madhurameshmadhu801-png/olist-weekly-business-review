-- Check 3: Payment total not matching item price + freight total (tolerance 0.01)
-- Policy: FLAGGED (financial variance due to interest installments, discounts, or vouchers)
-- Reason: Differences occur due to installment interest fees, voucher subsidies, or banking boleto rounding.
WITH items_agg AS (
    SELECT
        order_id,
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
)
SELECT
    o.order_id,
    ROUND(i.items_revenue + i.freight_total, 2) AS expected_total,
    p.payments_total,
    ROUND(p.payments_total - (i.items_revenue + i.freight_total), 2) AS variance
FROM stg_orders o
JOIN items_agg i ON o.order_id = i.order_id
JOIN payments_agg p ON o.order_id = p.order_id
WHERE ABS(p.payments_total - (i.items_revenue + i.freight_total)) > 0.01;
