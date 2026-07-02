import json
import os
import pandas as pd
from src.churn.train import train_churn
from src.churn.predict import ChurnScorer
from src.churn.model import ChurnModel
from src.churn.recommendations import RecommendationEngine
from src.churn.labeling import ChurnLabeler


def test_train_writes_artifacts(churn_mart, tmp_path):
    models_dir = str(tmp_path / "models")
    metrics = train_churn(mart=churn_mart, models_dir=models_dir)
    assert os.path.exists(os.path.join(models_dir, "model.pkl"))
    assert os.path.exists(os.path.join(models_dir, "metrics.json"))
    assert os.path.exists(os.path.join(models_dir, "feature_importance.json"))
    assert os.path.exists(os.path.join(models_dir, "drift_reference.json"))
    with open(os.path.join(models_dir, "metrics.json")) as f:
        saved = json.load(f)
    assert "xgboost" in saved and "baseline_logreg" in saved


def test_scorer_at_risk_shape(churn_mart, tmp_path):
    models_dir = str(tmp_path / "models")
    train_churn(mart=churn_mart, models_dir=models_dir)
    model = ChurnModel.load(os.path.join(models_dir, "model.pkl"))
    scorer = ChurnScorer(model, RecommendationEngine())
    cutoff = ChurnLabeler().cutoff(churn_mart)
    out = scorer.at_risk(churn_mart, cutoff)
    assert {"seller_id", "churn_probability", "recommendations"}.issubset(out.columns)
    assert (out["churn_probability"].between(0, 1)).all()
