import os
import shutil
import sqlite3
import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "mart.db")


def test_clean_fixture_passes_quality(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)  # must not raise
    assert os.path.exists(tmp_db)


def test_duplicate_seller_pk_raises(tmp_path):
    from src.etl import build_mart
    from src.errors import DataQualityError
    dirty = tmp_path / "dirty"
    shutil.copytree(FIXTURES, dirty)
    # inject a duplicate seller_id row
    sellers = dirty / "olist_sellers_dataset.csv"
    with open(sellers, "a", encoding="utf-8") as f:
        f.write("s1,99999,duplicate city,SP\n")
    with pytest.raises(DataQualityError) as exc:
        build_mart(data_dir=str(dirty), db_path=str(tmp_path / "d.db"))
    assert "seller" in str(exc.value).lower()


def test_null_customer_unique_id_raises(tmp_path):
    from src.etl import build_mart
    from src.errors import DataQualityError
    dirty = tmp_path / "dirty"
    shutil.copytree(FIXTURES, dirty)
    # inject a row with a blank customer_unique_id (parses as NULL)
    customers = dirty / "olist_customers_dataset.csv"
    with open(customers, "a", encoding="utf-8") as f:
        f.write("c99,,01000,sao paulo,SP\n")
    with pytest.raises(DataQualityError) as exc:
        build_mart(data_dir=str(dirty), db_path=str(tmp_path / "d.db"))
    assert "customer_unique_id" in str(exc.value).lower()
