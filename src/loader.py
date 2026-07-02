import pandas as pd
from src.mart import SalesMart


def load_data(db_path: str = "data/olist_mart.db") -> pd.DataFrame:
    return SalesMart(db_path).orders()
