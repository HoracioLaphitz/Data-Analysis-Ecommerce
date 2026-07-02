# Data Dictionary — olist_mart.db

## fact_orders (grain: one delivered order)
| column | type | source | cleaning | nullable |
|--------|------|--------|----------|----------|
| order_id | TEXT | raw_orders | delivered only | no |
| customer_id | TEXT | raw_orders | — | no |
| seller_id | TEXT | raw_order_items | first per order | yes |
| product_id | TEXT | raw_order_items | first per order | yes |
| date_id | TEXT | derived | date(purchase ts) | no |
| price | REAL | raw_order_items | sum, ≥0 | yes |
| freight_value | REAL | raw_order_items | sum | yes |
| payment_value | REAL | raw_payments | sum per order | yes |
| distance_km | REAL | Python Haversine | seller↔customer centroid | yes |
| delivery_delay_days | REAL | SQL julianday diff | delivered − estimated | yes |
| review_score | REAL | raw_reviews | mean per order, 1–5 | yes |
| order_status | TEXT | raw_orders | = 'delivered' | no |
| order_purchase_timestamp | TEXT | raw_orders | — | no |

## dim_sellers / dim_customers
| column | type | cleaning |
|--------|------|----------|
| *_id | TEXT | PK, not null, unique |
| *_state | TEXT | — |
| *_city | TEXT | LOWER(TRIM()) |
| lat, lng | REAL | ZIP centroid (mean) |

## dim_products
| column | type | cleaning |
|--------|------|----------|
| product_id | TEXT | PK |
| product_category_name_english | TEXT | translated |
| weight_g | REAL | — |
| volume_cm3 | REAL | length×height×width |

## dim_date
year, month, quarter, day_of_week derived from purchase timestamp.

## Views
- **v_seller_features** — seller × churn feature aggregates.
- **v_monthly_revenue**, **v_state_revenue** — analytics.
