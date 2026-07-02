import sqlite3
import pandas as pd


class SalesMart:
    """Repository — the only runtime SQL boundary. Returns DataFrames."""

    def __init__(self, db_path: str = "data/olist_mart.db") -> None:
        self._db_path = db_path

    def _read(self, sql: str, parse_dates=None) -> pd.DataFrame:
        conn = sqlite3.connect(self._db_path)
        try:
            return pd.read_sql_query(sql, conn, parse_dates=parse_dates)
        finally:
            conn.close()

    @property
    def max_order_date(self) -> pd.Timestamp:
        df = self._read(
            "SELECT MAX(order_purchase_timestamp) AS m FROM fact_orders")
        return pd.Timestamp(df["m"].iloc[0])

    def orders(self) -> pd.DataFrame:
        return self._read(
            """
            SELECT f.order_id, f.order_purchase_timestamp, f.order_status,
                   f.price, f.freight_value, f.payment_value,
                   f.distance_km, f.delivery_delay_days, f.review_score,
                   p.product_category_name_english, c.customer_state
            FROM fact_orders f
            JOIN dim_products  p ON f.product_id  = p.product_id
            JOIN dim_customers c ON f.customer_id = c.customer_id
            """,
            parse_dates=["order_purchase_timestamp"],
        )

    def customer_orders(self) -> pd.DataFrame:
        return self._read(
            """
            SELECT f.order_id, c.customer_unique_id,
                   f.order_purchase_timestamp, f.payment_value
            FROM fact_orders f
            JOIN dim_customers c ON f.customer_id = c.customer_id
            """,
            parse_dates=["order_purchase_timestamp"],
        )

    def seller_orders(self) -> pd.DataFrame:
        return self._read(
            """
            SELECT order_id, seller_id, order_purchase_timestamp,
                   payment_value, price, freight_value,
                   distance_km, delivery_delay_days, review_score
            FROM fact_orders
            WHERE seller_id IS NOT NULL
            """,
            parse_dates=["order_purchase_timestamp"],
        )

    def seller_features(self) -> pd.DataFrame:
        return self._read(
            "SELECT * FROM v_seller_features",
            parse_dates=["last_order_ts"],
        )
