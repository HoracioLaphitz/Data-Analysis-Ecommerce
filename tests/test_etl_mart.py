import os
import sqlite3
import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "mart.db")


def test_star_schema_tables(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    t = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert {"fact_orders", "dim_customers", "dim_sellers",
            "dim_products", "dim_date"}.issubset(t)


def test_fact_excludes_canceled(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    n = conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    conn.close()
    assert n == 2  # o1, o2


def test_fact_has_review_score(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    rows = {r[0]: r[1] for r in conn.execute(
        "SELECT order_id, review_score FROM fact_orders ORDER BY order_id").fetchall()}
    conn.close()
    assert rows["o1"] == pytest.approx(5.0)
    assert rows["o2"] == pytest.approx(2.0)


def test_fact_distance_positive_and_ordered(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    rows = {r[0]: r[1] for r in conn.execute(
        "SELECT order_id, distance_km FROM fact_orders ORDER BY order_id").fetchall()}
    conn.close()
    assert rows["o1"] > 0 and rows["o2"] > 0
    assert rows["o1"] < rows["o2"]  # SP-SP < RJ-SP


def test_indexes_exist(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    idx = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    conn.close()
    for name in ("idx_fact_seller", "idx_fact_customer",
                 "idx_fact_date", "idx_fact_product"):
        assert name in idx
