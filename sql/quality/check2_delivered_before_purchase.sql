-- Check 2: Delivered date earlier than purchase date in stg_orders
-- Policy: FLAGGED (temporal anomaly in logistics timestamps)
-- Reason: An order cannot realistically be delivered before purchase. Flagged for auditing.
SELECT
    order_id,
    order_purchase_timestamp,
    order_delivered_customer_date
FROM stg_orders
WHERE order_delivered_customer_date IS NOT NULL
  AND order_purchase_timestamp IS NOT NULL
  AND order_delivered_customer_date < order_purchase_timestamp;
