import os
import sqlite3
import numpy as np
import pandas as pd

from src.errors import DataQualityError

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")

_CSV_TO_RAW = {
    "olist_orders_dataset.csv": "raw_orders",
    "olist_order_items_dataset.csv": "raw_order_items",
    "olist_products_dataset.csv": "raw_products",
    "product_category_name_translation.csv": "raw_category_translation",
    "olist_order_payments_dataset.csv": "raw_payments",
    "olist_customers_dataset.csv": "raw_customers",
    "olist_sellers_dataset.csv": "raw_sellers",
    "olist_geolocation_dataset.csv": "raw_geolocation",
    "olist_order_reviews_dataset.csv": "raw_reviews",
}


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _run_sql(conn: sqlite3.Connection, filename: str) -> None:
    with open(os.path.join(SQL_DIR, filename), "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def _ingest_raw(conn: sqlite3.Connection, data_dir: str) -> None:
    for csv_name, table in _CSV_TO_RAW.items():
        df = pd.read_csv(os.path.join(data_dir, csv_name))
        df.to_sql(table, conn, if_exists="replace", index=False)


def _enrich_distance(conn: sqlite3.Connection) -> None:
    orders = pd.read_sql_query(
        "SELECT order_id, customer_id FROM stg_orders", conn)
    items = pd.read_sql_query(
        "SELECT order_id, seller_id FROM stg_order_items", conn)
    cust = pd.read_sql_query(
        "SELECT customer_id, lat AS c_lat, lng AS c_lng FROM stg_customers", conn)
    sell = pd.read_sql_query(
        "SELECT seller_id, lat AS s_lat, lng AS s_lng FROM stg_sellers", conn)

    df = (orders.merge(items, on="order_id", how="left")
                .merge(cust, on="customer_id", how="left")
                .merge(sell, on="seller_id", how="left"))
    df["distance_km"] = _haversine(
        df["c_lat"].values, df["c_lng"].values,
        df["s_lat"].values, df["s_lng"].values)
    df[["order_id", "distance_km"]].to_sql(
        "stg_order_distance", conn, if_exists="replace", index=False)


def _run_quality_checks(conn: sqlite3.Connection) -> None:
    path = os.path.join(SQL_DIR, "quality.sql")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    checks = []
    name = None
    buf = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- CHECK:"):
            if name and buf:
                checks.append((name, "\n".join(buf)))
            name = stripped.replace("-- CHECK:", "").strip()
            buf = []
        elif stripped and not stripped.startswith("--"):
            buf.append(line)
            if stripped.endswith(";"):
                checks.append((name, "\n".join(buf)))
                name, buf = None, []
    for check_name, sql in checks:
        rows = conn.execute(sql).fetchall()
        if rows:
            raise DataQualityError(
                f"Data-quality check failed: {check_name} ({len(rows)} rows)")


def build_mart(data_dir: str = "data", db_path: str = "data/olist_mart.db") -> None:
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        _ingest_raw(conn, data_dir)
        _run_sql(conn, "clean.sql")
        _enrich_distance(conn)
        _run_sql(conn, "mart.sql")
        _run_quality_checks(conn)
        _run_sql(conn, "views.sql")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    build_mart()
    print("Data mart built: data/olist_mart.db")
