import pytest
import pandas as pd
from src.loader import load_data


def test_load_data_returns_dataframe(test_db_path):
    df = load_data(test_db_path)
    assert df is not None
    assert len(df) > 0


def test_load_data_filters_delivered_only(test_db_path):
    df = load_data(test_db_path)
    assert (df["order_status"] == "delivered").all()


def test_load_data_has_required_columns(test_db_path):
    df = load_data(test_db_path)
    required = {
        "order_id", "order_purchase_timestamp", "order_status",
        "price", "freight_value", "payment_value",
        "product_category_name_english", "customer_state",
        "distance_km", "delivery_delay_days",
    }
    assert required.issubset(set(df.columns))


def test_load_data_parses_timestamps(test_db_path):
    df = load_data(test_db_path)
    assert pd.api.types.is_datetime64_any_dtype(df["order_purchase_timestamp"])


def test_load_data_payment_value_numeric(test_db_path):
    df = load_data(test_db_path)
    assert pd.api.types.is_numeric_dtype(df["payment_value"])


def test_load_data_distance_km_positive(test_db_path):
    df = load_data(test_db_path)
    assert (df["distance_km"] > 0).all()


def test_load_data_delivery_delay_numeric(test_db_path):
    df = load_data(test_db_path)
    assert pd.api.types.is_numeric_dtype(df["delivery_delay_days"])
