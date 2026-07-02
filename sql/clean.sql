-- Cleaning layer: raw_* -> stg_*. Idempotent. Assumptions in headers.

-- Geolocation: one centroid (mean lat/lng) per ZIP prefix.
DROP TABLE IF EXISTS stg_geolocation;
CREATE TABLE stg_geolocation AS
SELECT geolocation_zip_code_prefix AS zip,
       AVG(geolocation_lat) AS lat,
       AVG(geolocation_lng) AS lng
FROM raw_geolocation
GROUP BY geolocation_zip_code_prefix;

-- Customers: normalize city, attach centroid.
DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers AS
SELECT c.customer_id,
       c.customer_state,
       LOWER(TRIM(c.customer_city)) AS customer_city,
       g.lat, g.lng
FROM raw_customers c
LEFT JOIN stg_geolocation g ON c.customer_zip_code_prefix = g.zip
WHERE c.customer_id IS NOT NULL;

-- Sellers: normalize city, attach centroid.
DROP TABLE IF EXISTS stg_sellers;
CREATE TABLE stg_sellers AS
SELECT s.seller_id,
       s.seller_state,
       LOWER(TRIM(s.seller_city)) AS seller_city,
       g.lat, g.lng
FROM raw_sellers s
LEFT JOIN stg_geolocation g ON s.seller_zip_code_prefix = g.zip
WHERE s.seller_id IS NOT NULL;

-- Products: English category, weight, volume.
DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products AS
SELECT p.product_id,
       t.product_category_name_english,
       p.product_weight_g AS weight_g,
       (p.product_length_cm * p.product_height_cm * p.product_width_cm) AS volume_cm3
FROM raw_products p
LEFT JOIN raw_category_translation t
       ON p.product_category_name = t.product_category_name
WHERE p.product_id IS NOT NULL;

-- Orders: cast, delivery delay in SQL, delivered only, valid dates.
DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders AS
SELECT order_id,
       customer_id,
       order_status,
       order_purchase_timestamp,
       (julianday(order_delivered_customer_date)
        - julianday(order_estimated_delivery_date)) AS delivery_delay_days
FROM raw_orders
WHERE order_status = 'delivered'
  AND order_id IS NOT NULL
  AND order_purchase_timestamp IS NOT NULL;

-- Order items: first seller/product per order, summed price/freight; drop negatives.
DROP TABLE IF EXISTS stg_order_items;
CREATE TABLE stg_order_items AS
SELECT order_id,
       MIN(seller_id)  AS seller_id,
       MIN(product_id) AS product_id,
       SUM(price)         AS price,
       SUM(freight_value) AS freight_value
FROM raw_order_items
WHERE price >= 0
GROUP BY order_id;

-- Payments: total per order.
DROP TABLE IF EXISTS stg_payments;
CREATE TABLE stg_payments AS
SELECT order_id, SUM(payment_value) AS payment_value
FROM raw_payments
GROUP BY order_id;

-- Reviews: mean score per order, clamped to 1..5.
DROP TABLE IF EXISTS stg_reviews;
CREATE TABLE stg_reviews AS
SELECT order_id, AVG(review_score) AS review_score
FROM raw_reviews
WHERE review_score BETWEEN 1 AND 5
GROUP BY order_id;
