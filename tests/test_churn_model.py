import numpy as np
import pandas as pd
import pytest
from src.churn.model import ChurnModel


@pytest.fixture
def xy():
    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame({
        "recency_days": rng.uniform(0, 200, n),
        "frequency": rng.integers(1, 20, n).astype(float),
        "monetary_total": rng.uniform(50, 5000, n),
        "monetary_aov": rng.uniform(20, 500, n),
        "tenure_days": rng.uniform(0, 400, n),
        "avg_delivery_delay_days": rng.uniform(-10, 20, n),
        "pct_late": rng.uniform(0, 1, n),
        "avg_distance_km": rng.uniform(0, 1000, n),
        "avg_review_score": rng.uniform(1, 5, n),
        "pct_low_review": rng.uniform(0, 1, n),
        "category_diversity": rng.integers(1, 10, n).astype(float),
        "has_reviews": rng.integers(0, 2, n).astype(float),
    })
    # churn correlates with high recency + high pct_late
    logit = 0.02 * X["recency_days"] + 2.0 * X["pct_late"] - 3
    p = 1 / (1 + np.exp(-logit))
    y = pd.Series((rng.uniform(0, 1, n) < p).astype(int), name="churned")
    return X, y


@pytest.mark.parametrize("estimator", ["logreg", "xgboost"])
def test_fit_predict_proba_shape(xy, estimator):
    X, y = xy
    model = ChurnModel(estimator).fit(X, y)
    p = model.predict_proba(X)
    assert p.shape == (len(X),)
    assert ((p >= 0) & (p <= 1)).all()


def test_evaluate_keys(xy):
    X, y = xy
    metrics = ChurnModel("xgboost").fit(X, y).evaluate(X, y)
    for k in ("auc_roc", "pr_auc", "precision", "recall", "f1", "confusion_matrix"):
        assert k in metrics


def test_feature_importance(xy):
    X, y = xy
    imp = ChurnModel("xgboost").fit(X, y).feature_importance()
    assert set(imp).issubset(set(X.columns))
    assert all(v >= 0 for v in imp.values())


def test_save_load_roundtrip(xy, tmp_path):
    X, y = xy
    model = ChurnModel("xgboost").fit(X, y)
    path = str(tmp_path / "model.pkl")
    model.save(path)
    loaded = ChurnModel.load(path)
    assert np.allclose(loaded.predict_proba(X), model.predict_proba(X))
