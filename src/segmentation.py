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


class CohortBuilder:
    """Monthly cohort retention matrix, keyed by month of first purchase
    (customer_unique_id grain)."""

    def build(self, mart, window_months: int = 12) -> pd.DataFrame:
        orders = mart.customer_orders()
        orders = orders.assign(
            order_month=orders["order_purchase_timestamp"].dt.to_period("M")
        )
        first_month = orders.groupby("customer_unique_id")["order_month"].min()
        orders = orders.join(first_month.rename("cohort_month"), on="customer_unique_id")
        orders["month_offset"] = (orders["order_month"] - orders["cohort_month"]).apply(lambda p: p.n)
        orders = orders[orders["month_offset"].between(0, window_months)]

        cohort_sizes = (
            orders[orders["month_offset"] == 0]
            .groupby("cohort_month")["customer_unique_id"].nunique()
        )

        active = (
            orders.groupby(["cohort_month", "month_offset"])["customer_unique_id"]
            .nunique()
            .reset_index(name="active_customers")
        )
        active["cohort_size"] = active["cohort_month"].map(cohort_sizes)
        active["retention_pct"] = active["active_customers"] / active["cohort_size"] * 100

        matrix = active.pivot(index="cohort_month", columns="month_offset", values="retention_pct")

        # A cohort that hasn't had enough elapsed time to reach a given month
        # offset must show as "no data yet" (NaN), never as "0% retained" —
        # otherwise recent cohorts look like total churn when they simply
        # haven't had the chance to return yet.
        max_month = orders["order_month"].max()
        for cohort_month in matrix.index:
            for offset in matrix.columns:
                if cohort_month + offset > max_month:
                    matrix.loc[cohort_month, offset] = float("nan")
        return matrix
