-- Check 4: Orders with no matching customer record
-- Policy: BLOCKING (critical referential integrity)
-- Reason: Every order must belong to a registered customer.
SELECT
    o.order_id,
    o.customer_id
FROM stg_orders o
LEFT JOIN stg_customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
