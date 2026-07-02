"""Produce a deploy-sized copy of the data mart.

Drops the raw_* ingestion tables and stg_* staging tables (only needed
while building the mart) and vacuums the file. The star schema, views and
quality-checked data are untouched, so the app and the churn pipeline read
the slim mart exactly like the full one (~213 MB -> ~50 MB).

Usage:
    python scripts/slim_mart.py [source_db] [target_db]

Defaults: data/olist_mart.db -> data/olist_mart_slim.db
"""
import shutil
import sqlite3
import sys


def slim_mart(source: str, target: str) -> None:
    shutil.copyfile(source, target)
    conn = sqlite3.connect(target)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        if table.startswith(("raw_", "stg_")):
            conn.execute(f"DROP TABLE {table}")
    conn.commit()
    conn.execute("VACUUM")
    conn.close()


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "data/olist_mart.db"
    target = sys.argv[2] if len(sys.argv) > 2 else "data/olist_mart_slim.db"
    slim_mart(source, target)
    print(f"Slim mart written to {target}")
