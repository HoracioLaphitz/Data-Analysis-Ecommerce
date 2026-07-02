import pandas as pd
import pytest
from src.mart import SalesMart


def test_orders_columns(test_db_path):
    df = SalesMart(test_db_path).orders()
    required = {"order_id", "order_purchase_timestamp", "order_status",
                "price", "freight_value", "payment_value",
                "product_category_name_english", "customer_state",
                "distance_km", "delivery_delay_days", "review_score"}
    assert required.issubset(df.columns)


def test_max_order_date_is_timestamp(test_db_path):
    d = SalesMart(test_db_path).max_order_date
    assert isinstance(d, pd.Timestamp)


def test_seller_orders_has_seller_and_ts(test_db_path):
    df = SalesMart(test_db_path).seller_orders()
    assert {"seller_id", "order_purchase_timestamp", "review_score"}.issubset(df.columns)


def test_seller_features_indexed(test_db_path):
    df = SalesMart(test_db_path).seller_features()
    assert "seller_id" in df.columns
    assert "frequency" in df.columns
