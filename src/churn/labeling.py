import pandas as pd


class ChurnLabeler:
    """Cohort labeling: features precede the label window (no leakage)."""

    def __init__(self, horizon_days: int = 90) -> None:
        self.horizon_days = horizon_days

    def cutoff(self, mart) -> pd.Timestamp:
        return mart.max_order_date.normalize() - pd.Timedelta(days=self.horizon_days)

    def label(self, mart) -> pd.DataFrame:
        orders = mart.seller_orders()
        cutoff = self.cutoff(mart)
        window_end = cutoff + pd.Timedelta(days=self.horizon_days)

        ts = orders["order_purchase_timestamp"]
        before = orders[ts <= cutoff]
        future = orders[(ts > cutoff) & (ts <= window_end)]

        eligible = set(before["seller_id"].unique())
        if not eligible:
            raise ValueError("No eligible sellers in the observation window.")
        active_future = set(future["seller_id"].unique())

        records = [
            {"seller_id": s, "churned": 0 if s in active_future else 1}
            for s in sorted(eligible)
        ]
        return pd.DataFrame(records, columns=["seller_id", "churned"])
