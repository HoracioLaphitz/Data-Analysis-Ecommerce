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
                "Mejorar logística: más del 30% de las entregas llegan tarde.")
        if seller_features.get("avg_review_score", 5) < self.LOW_REVIEW_THRESHOLD:
            recs.append(
                "Atender calidad: baja satisfacción del cliente (review promedio < 3).")
        if seller_features.get("recency_days", 0) > self.INACTIVE_DAYS:
            recs.append(
                "Reactivar: vendedor inactivo hace más de 60 días.")
        return recs
