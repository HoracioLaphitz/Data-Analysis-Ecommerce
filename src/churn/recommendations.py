import pandas as pd


class RecommendationEngine:
    """Rules-based, offline business recommendations from seller features."""

    LATE_THRESHOLD = 0.3
    LOW_REVIEW_THRESHOLD = 3.0
    INACTIVE_DAYS = 60

    def recommend(self, seller_features: pd.Series) -> list[str]:
        recs: list[str] = []
        if seller_features.get("pct_late", 0) > self.LATE_THRESHOLD:
            recs.append(
                "Improve logistics: over 30% of deliveries are late.")
        if seller_features.get("avg_review_score", 5) < self.LOW_REVIEW_THRESHOLD:
            recs.append(
                "Address quality: low customer satisfaction (avg review < 3).")
        if seller_features.get("recency_days", 0) > self.INACTIVE_DAYS:
            recs.append(
                "Re-engage: seller inactive for 60+ days.")
        return recs
