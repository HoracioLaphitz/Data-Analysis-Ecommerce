-- Mart layer: build Star Schema from stg_* (+ stg_order_distance from Python).

DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers AS
SELECT customer_id, customer_unique_id, customer_state, customer_city, lat, lng
FROM stg_customers;

DROP TABLE IF EXISTS dim_sellers;
CREATE TABLE dim_sellers AS
SELECT seller_id, seller_state, seller_city, lat, lng FROM stg_sellers;

DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products AS
SELECT product_id, product_category_name_english, weight_g, volume_cm3
FROM stg_products;

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date AS
SELECT DISTINCT
    date(order_purchase_timestamp) AS date_id,
    CAST(strftime('%Y', order_purchase_timestamp) AS INTEGER) AS year,
    CAST(strftime('%m', order_purchase_timestamp) AS INTEGER) AS month,
    ((CAST(strftime('%m', order_purchase_timestamp) AS INTEGER) - 1) / 3 + 1) AS quarter,
    CAST(strftime('%w', order_purchase_timestamp) AS INTEGER) AS day_of_week
FROM stg_orders;

DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders AS
SELECT
    o.order_id,
    o.customer_id,
    i.seller_id,
    i.product_id,
    date(o.order_purchase_timestamp) AS date_id,
    i.price,
    i.freight_value,
    p.payment_value,
    d.distance_km,
    o.delivery_delay_days,
    r.review_score,
    o.order_status,
    o.order_purchase_timestamp
FROM stg_orders o
LEFT JOIN stg_order_items    i ON o.order_id = i.order_id
LEFT JOIN stg_payments       p ON o.order_id = p.order_id
LEFT JOIN stg_order_distance d ON o.order_id = d.order_id
LEFT JOIN stg_reviews        r ON o.order_id = r.order_id;

CREATE INDEX idx_fact_seller   ON fact_orders(seller_id);
CREATE INDEX idx_fact_customer ON fact_orders(customer_id);
CREATE INDEX idx_fact_date     ON fact_orders(date_id);
CREATE INDEX idx_fact_product  ON fact_orders(product_id);
