import os
from src.mart import SalesMart


def profile_mart(db_path: str = "data/olist_mart.db",
                 output_path: str = "reports/eda.html") -> str:
    from ydata_profiling import ProfileReport

    df = SalesMart(db_path).seller_features()
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    report = ProfileReport(df, title="Olist Seller Features EDA", minimal=True)
    report.to_file(output_path)
    return output_path


if __name__ == "__main__":
    path = profile_mart()
    print(f"EDA report: {path}")
