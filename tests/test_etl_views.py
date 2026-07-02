import os
import sqlite3
import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "mart.db")


def test_views_exist(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    v = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'").fetchall()}
    conn.close()
    assert {"v_seller_features", "v_monthly_revenue", "v_state_revenue"}.issubset(v)


def test_seller_features_columns(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(v_seller_features)").fetchall()}
    conn.close()
    for c in ("seller_id", "frequency", "avg_review_score", "pct_late",
              "avg_distance_km", "category_diversity", "last_order_ts"):
        assert c in cols


def test_seller_features_frequency(tmp_db):
    # s1 sold o1+o2 (both delivered) -> frequency 2
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    freq = conn.execute(
        "SELECT frequency FROM v_seller_features WHERE seller_id='s1'").fetchone()[0]
    conn.close()
    assert freq == 2
