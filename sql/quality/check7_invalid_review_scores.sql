-- Check 7: Review scores outside valid range (1 to 5) or duplicate review IDs
-- Policy: FLAGGED (survey validity and rating scale integrity)
-- Reason: Review scores must be on a 1-5 integer scale; duplicates reflect re-submissions.
SELECT
    review_id,
    order_id,
    review_score,
    'OUT_OF_RANGE' AS dq_issue
FROM stg_order_reviews
WHERE review_score < 1 OR review_score > 5
UNION ALL
SELECT
    review_id,
    order_id,
    review_score,
    'DUPLICATE_REVIEW_ID' AS dq_issue
FROM stg_order_reviews
WHERE review_id IN (
    SELECT review_id
    FROM stg_order_reviews
    GROUP BY review_id
    HAVING COUNT(*) > 1
);
