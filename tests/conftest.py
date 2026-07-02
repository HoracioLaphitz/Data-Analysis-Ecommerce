import os
import tempfile
import pytest
import pandas as pd
from datetime import datetime

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_df():
    """One row per order — matches load_data() output after SQLite refactor.

    payment_value sum = 638, order_id.nunique() = 3 — identical to previous fixture totals.
    """
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3"],
        "order_purchase_timestamp": [
            datetime(2018, 1, 15),
            datetime(2018, 3, 10),
            datetime(2018, 6, 5),
        ],
        "order_status": ["delivered", "delivered", "delivered"],
        "price": [150.0, 280.0, 150.0],
        "freight_value": [15.0, 28.0, 15.0],
        "payment_value": [165.0, 308.0, 165.0],
        "product_category_name_english": ["electronics", "electronics", "books"],
        "customer_state": ["SP", "RJ", "MG"],
        "distance_km": [9.0, 368.0, 430.0],
        "delivery_delay_days": [-5.0, 5.0, 0.0],
    })


@pytest.fixture(scope="session")
def test_db_path():
    """SQLite Data Mart built from fixture CSVs — created once per test session."""
    from src.etl import build_mart

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    build_mart(data_dir=FIXTURES, db_path=db)
    yield db
    os.unlink(db)


@pytest.fixture
def churn_mart(tmp_path):
    """SalesMart over a hand-built mart with controlled seller timelines.

    max_order_date = 2018-08-01. cutoff (horizon 90) = 2018-05-03.
      sA: orders before and after cutoff  -> churned 0
      sB: orders only before cutoff       -> churned 1
      sC: orders only after cutoff        -> excluded (not eligible)
    """
    import sqlite3
    from src.mart import SalesMart
    db = str(tmp_path / "churn.db")
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE fact_orders (
            order_id TEXT, customer_id TEXT, seller_id TEXT, product_id TEXT,
            date_id TEXT, price REAL, freight_value REAL, payment_value REAL,
            distance_km REAL, delivery_delay_days REAL, review_score REAL,
            order_status TEXT, order_purchase_timestamp TEXT);
        """
    )
    rows = [
        # sA before + after cutoff
        ("a1", "c1", "sA", "p1", "2018-02-01", 100, 10, 110, 50, -2, 5, "delivered", "2018-02-01 10:00:00"),
        ("a2", "c2", "sA", "p1", "2018-07-01", 120, 12, 132, 60,  3, 4, "delivered", "2018-07-01 10:00:00"),
        # sB only before cutoff -> churned
        ("b1", "c3", "sB", "p2", "2018-01-10", 200, 20, 220, 80,  5, 2, "delivered", "2018-01-10 10:00:00"),
        ("b2", "c4", "sB", "p2", "2018-03-15", 150, 15, 165, 90,  1, 3, "delivered", "2018-03-15 10:00:00"),
        # sC only after cutoff -> excluded
        ("d1", "c5", "sC", "p1", "2018-07-20", 300, 30, 330, 40, -1, 5, "delivered", "2018-07-20 10:00:00"),
        # anchor max date
        ("z1", "c6", "sA", "p1", "2018-08-01", 100, 10, 110, 50,  0, 5, "delivered", "2018-08-01 10:00:00"),
    ]
    conn.executemany(
        "INSERT INTO fact_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return SalesMart(db)


@pytest.fixture
def segmentation_mart(tmp_path):
    """SalesMart over a hand-built mart with controlled repeat-purchase and
    recency patterns, to exercise RFM scoring and cohort-masking edge cases.

    u1: two orders, Jan and Mar 2018 -> repeat customer, cohort=2018-01
    u2: one order, Jan 2018          -> single-purchase, cohort=2018-01
    u3: one order, Jul 2018 (the last month in this fixture) -> cohort=2018-07,
        too recent to have reached month_offset=3 -> must be NaN, not 0.
    """
    import sqlite3
    from src.mart import SalesMart
    db = str(tmp_path / "segmentation.db")
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE fact_orders (
            order_id TEXT, customer_id TEXT, order_purchase_timestamp TEXT,
            payment_value REAL);
        CREATE TABLE dim_customers (
            customer_id TEXT, customer_unique_id TEXT);
        """
    )
    conn.executemany(
        "INSERT INTO fact_orders VALUES (?,?,?,?)",
        [
            ("o1", "c1", "2018-01-10 10:00:00", 100.0),
            ("o2", "c1b", "2018-03-15 10:00:00", 50.0),
            ("o3", "c2", "2018-01-20 10:00:00", 200.0),
            ("o4", "c3", "2018-07-05 10:00:00", 80.0),
        ],
    )
    conn.executemany(
        "INSERT INTO dim_customers VALUES (?,?)",
        [("c1", "u1"), ("c1b", "u1"), ("c2", "u2"), ("c3", "u3")],
    )
    conn.commit()
    conn.close()
    return SalesMart(db)
