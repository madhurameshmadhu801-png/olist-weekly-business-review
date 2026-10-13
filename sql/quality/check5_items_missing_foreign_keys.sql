-- Check 5: Order items referencing missing orders, products or sellers
-- Policy: BLOCKING (critical referential integrity)
-- Reason: Line items cannot be orphaned without a valid parent order, product, or seller.
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    CASE
        WHEN o.order_id IS NULL THEN 'MISSING_ORDER'
        WHEN p.product_id IS NULL THEN 'MISSING_PRODUCT'
        WHEN s.seller_id IS NULL THEN 'MISSING_SELLER'
    END AS missing_entity
FROM stg_order_items i
LEFT JOIN stg_orders o ON i.order_id = o.order_id
LEFT JOIN stg_products p ON i.product_id = p.product_id
LEFT JOIN stg_sellers s ON i.seller_id = s.seller_id
WHERE o.order_id IS NULL
   OR p.product_id IS NULL
   OR s.seller_id IS NULL;
