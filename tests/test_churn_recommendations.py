import pandas as pd
from src.churn.recommendations import RecommendationEngine


def test_late_deliveries_flagged():
    s = pd.Series({"pct_late": 0.4, "avg_review_score": 4.5,
                   "recency_days": 10, "avg_distance_km": 100})
    recs = RecommendationEngine().recommend(s)
    assert any("logística" in r.lower() or "tarde" in r.lower() for r in recs)


def test_low_reviews_flagged():
    s = pd.Series({"pct_late": 0.05, "avg_review_score": 2.5,
                   "recency_days": 10, "avg_distance_km": 100})
    recs = RecommendationEngine().recommend(s)
    assert any("calidad" in r.lower() or "satisfacción" in r.lower() for r in recs)


def test_inactive_flagged():
    s = pd.Series({"pct_late": 0.05, "avg_review_score": 4.5,
                   "recency_days": 90, "avg_distance_km": 100})
    recs = RecommendationEngine().recommend(s)
    assert any("reactivar" in r.lower() or "inactivo" in r.lower() for r in recs)


def test_healthy_seller_no_recs():
    s = pd.Series({"pct_late": 0.02, "avg_review_score": 4.8,
                   "recency_days": 5, "avg_distance_km": 100})
    assert RecommendationEngine().recommend(s) == []
