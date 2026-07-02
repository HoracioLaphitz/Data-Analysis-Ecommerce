-- Data-quality gate. Each labelled SELECT must return ZERO rows.

-- CHECK: dim_sellers_no_null_pk
SELECT seller_id FROM dim_sellers WHERE seller_id IS NULL;

-- CHECK: dim_customers_no_null_pk
SELECT customer_id FROM dim_customers WHERE customer_id IS NULL;

-- CHECK: dim_sellers_unique_pk
SELECT seller_id FROM dim_sellers GROUP BY seller_id HAVING COUNT(*) > 1;

-- CHECK: dim_customers_unique_pk
SELECT customer_id FROM dim_customers GROUP BY customer_id HAVING COUNT(*) > 1;

-- CHECK: dim_products_unique_pk
SELECT product_id FROM dim_products GROUP BY product_id HAVING COUNT(*) > 1;

-- CHECK: fact_seller_referential_integrity
SELECT f.order_id FROM fact_orders f
LEFT JOIN dim_sellers s ON f.seller_id = s.seller_id
WHERE f.seller_id IS NOT NULL AND s.seller_id IS NULL;

-- CHECK: fact_customer_referential_integrity
SELECT f.order_id FROM fact_orders f
LEFT JOIN dim_customers c ON f.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- CHECK: fact_price_non_negative
SELECT order_id FROM fact_orders WHERE price < 0;

-- CHECK: fact_review_score_in_range
SELECT order_id FROM fact_orders
WHERE review_score IS NOT NULL AND (review_score < 1 OR review_score > 5);

-- CHECK: fact_distance_non_negative
SELECT order_id FROM fact_orders WHERE distance_km < 0;

-- CHECK: fact_non_empty
SELECT 1 WHERE (SELECT COUNT(*) FROM fact_orders) = 0;

-- CHECK: dim_customers_customer_unique_id_not_null
SELECT customer_id FROM dim_customers WHERE customer_unique_id IS NULL;
