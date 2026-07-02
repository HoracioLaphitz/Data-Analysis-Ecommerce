import pandas as pd


class RFMBuilder:
    """Classic RFM scoring per customer_unique_id (not customer_id — see
    docs/data-dictionary.md for why customer_id can't detect repeat buyers)."""

    def build(self, mart, reference_date: pd.Timestamp | None = None) -> pd.DataFrame:
        orders = mart.customer_orders()
        if reference_date is None:
            reference_date = orders["order_purchase_timestamp"].max()

        g = orders.groupby("customer_unique_id")
        rfm = pd.DataFrame({
            "recency_days": (reference_date - g["order_purchase_timestamp"].max()).dt.days.astype(float),
            "frequency": g["order_id"].nunique().astype(float),
            "monetary": g["payment_value"].sum(),
        })

        # rank(method="first") breaks ties before qcut so equal recency/monetary
        # values don't collide into a single bin edge.
        rfm["R"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
        # Frequency is NOT quintile-scored: ~97% of Olist customers place a
        # single order (verified against raw data), so a quantile split would
        # assign arbitrary, meaningless different scores to identical behavior.
        # Cap the raw order count instead — 1 order = score 1, 5+ orders = score 5.
        rfm["F"] = rfm["frequency"].clip(upper=5).astype(int)
        rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

        rfm["segment"] = rfm.apply(self._segment, axis=1)
        return rfm

    @staticmethod
    def _segment(row) -> str:
        r, f = row["R"], row["F"]
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 3 and f >= 4:
            return "Loyal"
        if r >= 4 and f <= 3:
            return "New Customers"
        if r <= 2 and f >= 3:
            return "At Risk"
        if r <= 2 and f <= 2:
            return "Hibernating"
        return "Need Attention"
