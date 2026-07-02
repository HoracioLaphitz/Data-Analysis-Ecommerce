import pandas as pd

from src.churn.features import SellerFeatureBuilder
from src.churn.model import ChurnModel
from src.churn.recommendations import RecommendationEngine


class ChurnScorer:
    """Scores current sellers and attaches business recommendations."""

    def __init__(self, model: ChurnModel, engine: RecommendationEngine) -> None:
        self._model = model
        self._engine = engine

    def at_risk(self, mart, cutoff: pd.Timestamp) -> pd.DataFrame:
        features = SellerFeatureBuilder().build(mart, cutoff)
        proba = self._model.predict_proba(features)
        out = pd.DataFrame({
            "seller_id": features.index,
            "churn_probability": proba,
        })
        out["recommendations"] = [
            self._engine.recommend(features.loc[sid])
            for sid in features.index
        ]
        return out.sort_values("churn_probability", ascending=False).reset_index(drop=True)
