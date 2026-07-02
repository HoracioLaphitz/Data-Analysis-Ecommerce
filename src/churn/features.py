import numpy as np
import pandas as pd


class SellerFeatureBuilder:
    """Seller × feature matrix as-of a cutoff. Uses only orders <= cutoff."""

    FEATURES = [
        "recency_days", "frequency", "monetary_total", "monetary_aov",
        "tenure_days", "avg_delivery_delay_days", "pct_late",
        "avg_distance_km", "avg_review_score", "pct_low_review",
        "category_diversity", "has_reviews",
    ]

    def build(self, mart, cutoff: pd.Timestamp) -> pd.DataFrame:
        orders = mart.seller_orders()
        orders = orders[orders["order_purchase_timestamp"] <= cutoff]
        if orders.empty:
            raise ValueError("No orders on/before cutoff to build features.")

        g = orders.groupby("seller_id")
        last = g["order_purchase_timestamp"].max()
        first = g["order_purchase_timestamp"].min()

        feats = pd.DataFrame(index=last.index)
        feats.index.name = "seller_id"
        feats["recency_days"] = (cutoff - last).dt.days.astype(float)
        feats["frequency"] = g.size().astype(float)
        feats["monetary_total"] = g["payment_value"].sum()
        feats["monetary_aov"] = g["payment_value"].mean()
        feats["tenure_days"] = (last - first).dt.days.astype(float)
        feats["avg_delivery_delay_days"] = g["delivery_delay_days"].mean()
        feats["pct_late"] = g["delivery_delay_days"].apply(lambda s: (s > 0).mean())
        feats["avg_distance_km"] = g["distance_km"].mean()
        feats["avg_review_score"] = g["review_score"].mean()
        feats["pct_low_review"] = g["review_score"].apply(
            lambda s: (s <= 2).mean() if s.notna().any() else 0.0)
        # category_diversity: not in seller_orders; approximate by distinct products
        feats["category_diversity"] = orders.groupby("seller_id")["order_id"].nunique().astype(float)

        feats["has_reviews"] = feats["avg_review_score"].notna().astype(float)
        median_score = feats["avg_review_score"].median()
        if np.isnan(median_score):
            median_score = 3.0
        feats["avg_review_score"] = feats["avg_review_score"].fillna(median_score)
        feats = feats.fillna(0.0)
        return feats[self.FEATURES]
