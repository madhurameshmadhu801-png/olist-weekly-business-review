-- Check 6: Delivered orders missing a delivered timestamp
-- Policy: FLAGGED (status/timestamp inconsistency in logistics tracking)
-- Reason: Orders marked 'delivered' must have a delivery timestamp; missing values require operational investigation.
SELECT
    order_id,
    order_status,
    order_delivered_customer_date
FROM stg_orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NULL;
