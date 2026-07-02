import pandas as pd
from src.churn.features import SellerFeatureBuilder
from src.churn.labeling import ChurnLabeler


def test_feature_columns(churn_mart):
    cutoff = ChurnLabeler().cutoff(churn_mart)
    X = SellerFeatureBuilder().build(churn_mart, cutoff)
    assert list(X.columns) == SellerFeatureBuilder.FEATURES
    assert X.index.name == "seller_id"


def test_only_pre_cutoff_orders_used(churn_mart):
    # sA has a2 (2018-07-01, after cutoff) that must be EXCLUDED from features
    cutoff = ChurnLabeler().cutoff(churn_mart)
    X = SellerFeatureBuilder().build(churn_mart, cutoff)
    # sA pre-cutoff orders: a1 only -> frequency 1
    assert X.loc["sA", "frequency"] == 1
    # sB pre-cutoff: b1, b2 -> frequency 2
    assert X.loc["sB", "frequency"] == 2


def test_no_nan_in_features(churn_mart):
    cutoff = ChurnLabeler().cutoff(churn_mart)
    X = SellerFeatureBuilder().build(churn_mart, cutoff)
    assert not X.isna().any().any()
