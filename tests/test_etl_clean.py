import os
import sqlite3
import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "mart.db")


def _tables(db):
    conn = sqlite3.connect(db)
    t = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    return t


def test_raw_tables_loaded(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    t = _tables(tmp_db)
    for name in ("raw_orders", "raw_reviews", "raw_geolocation"):
        assert name in t


def test_stg_geolocation_dedup_to_centroid(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT COUNT(*) FROM stg_geolocation").fetchone()[0]
    distinct_zip = conn.execute(
        "SELECT COUNT(DISTINCT zip) FROM stg_geolocation").fetchone()[0]
    conn.close()
    assert rows == distinct_zip  # one centroid per ZIP


def test_stg_reviews_mean_per_order(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    score = conn.execute(
        "SELECT review_score FROM stg_reviews WHERE order_id='o1'").fetchone()[0]
    conn.close()
    assert score == pytest.approx(5.0)  # mean of rv1,rv2


def test_stg_orders_delivery_delay_in_sql(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    rows = {r[0]: r[1] for r in conn.execute(
        "SELECT order_id, delivery_delay_days FROM stg_orders ORDER BY order_id").fetchall()}
    conn.close()
    assert rows["o1"] == pytest.approx(-5.0)
    assert rows["o2"] == pytest.approx(5.0)


def test_data_quality_error_exists():
    from src.errors import DataQualityError
    assert issubclass(DataQualityError, Exception)
