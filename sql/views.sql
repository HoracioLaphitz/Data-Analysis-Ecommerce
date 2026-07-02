-- Analytical views. Auditable in DB Browser.

DROP VIEW IF EXISTS v_monthly_revenue;
CREATE VIEW v_monthly_revenue AS
SELECT strftime('%Y-%m', order_purchase_timestamp) AS month,
       SUM(payment_value) AS revenue
FROM fact_orders
GROUP BY month
ORDER BY month;

DROP VIEW IF EXISTS v_state_revenue;
CREATE VIEW v_state_revenue AS
SELECT c.customer_state, SUM(f.payment_value) AS revenue
FROM fact_orders f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY c.customer_state;

DROP VIEW IF EXISTS v_seller_features;
CREATE VIEW v_seller_features AS
WITH maxd AS (SELECT MAX(order_purchase_timestamp) AS m FROM fact_orders)
SELECT
    f.seller_id,
    julianday((SELECT m FROM maxd)) - julianday(MAX(f.order_purchase_timestamp))
        AS recency_days,
    COUNT(*) AS frequency,
    SUM(f.payment_value) AS monetary_total,
    AVG(f.payment_value) AS monetary_aov,
    julianday(MAX(f.order_purchase_timestamp))
        - julianday(MIN(f.order_purchase_timestamp)) AS tenure_days,
    AVG(f.delivery_delay_days) AS avg_delivery_delay_days,
    AVG(CASE WHEN f.delivery_delay_days > 0 THEN 1.0 ELSE 0.0 END) AS pct_late,
    AVG(f.distance_km) AS avg_distance_km,
    AVG(f.review_score) AS avg_review_score,
    AVG(CASE WHEN f.review_score <= 2 THEN 1.0 ELSE 0.0 END) AS pct_low_review,
    COUNT(DISTINCT p.product_category_name_english) AS category_diversity,
    MAX(f.order_purchase_timestamp) AS last_order_ts
FROM fact_orders f
LEFT JOIN dim_products p ON f.product_id = p.product_id
GROUP BY f.seller_id;
