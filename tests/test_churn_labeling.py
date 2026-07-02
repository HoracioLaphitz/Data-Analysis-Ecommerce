import pandas as pd
from src.churn.labeling import ChurnLabeler


def test_cutoff_is_max_minus_horizon(churn_mart):
    cutoff = ChurnLabeler(horizon_days=90).cutoff(churn_mart)
    assert cutoff == pd.Timestamp("2018-08-01 00:00:00") - pd.Timedelta(days=90)


def test_labels(churn_mart):
    labels = ChurnLabeler(horizon_days=90).label(churn_mart)
    m = dict(zip(labels["seller_id"], labels["churned"]))
    assert m["sA"] == 0            # active after cutoff
    assert m["sB"] == 1            # silent after cutoff
    assert "sC" not in m           # not eligible (no orders <= cutoff)


def test_label_columns(churn_mart):
    labels = ChurnLabeler().label(churn_mart)
    assert list(labels.columns) == ["seller_id", "churned"]
