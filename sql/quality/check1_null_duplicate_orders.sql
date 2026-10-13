-- Check 1: Null or duplicate order_id in stg_orders
-- Policy: BLOCKING (critical primary key constraint)
-- Reason: Every order must have a unique, non-null identifier.
SELECT
    order_id,
    COUNT(*) AS occurrence_count
FROM stg_orders
GROUP BY order_id
HAVING order_id IS NULL OR COUNT(*) > 1;
