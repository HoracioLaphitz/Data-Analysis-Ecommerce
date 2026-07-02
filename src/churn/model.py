import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


class ChurnModel:
    """Wraps a LogReg baseline or XGBoost estimator behind one interface."""

    def __init__(self, estimator: str = "xgboost") -> None:
        if estimator not in ("logreg", "xgboost"):
            raise ValueError(f"Unknown estimator: {estimator}")
        self.estimator = estimator
        self._features: list[str] | None = None
        if estimator == "logreg":
            self._model = Pipeline([
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
            ])
        else:
            self._model = XGBClassifier(
                n_estimators=200, max_depth=4, learning_rate=0.1,
                subsample=0.9, eval_metric="logloss", random_state=0)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ChurnModel":
        self._features = list(X.columns)
        if self.estimator == "xgboost":
            pos = max(int((y == 1).sum()), 1)
            neg = int((y == 0).sum())
            self._model.set_params(scale_pos_weight=neg / pos)
        self._model.fit(X, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self._model.predict_proba(X[self._features])[:, 1]

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        p = self.predict_proba(X)
        pred = (p >= 0.5).astype(int)
        return {
            "auc_roc": float(roc_auc_score(y, p)),
            "pr_auc": float(average_precision_score(y, p)),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)),
            "confusion_matrix": confusion_matrix(y, pred).tolist(),
        }

    def feature_importance(self) -> dict:
        if self.estimator == "xgboost":
            vals = self._model.feature_importances_
        else:
            coefs = self._model.named_steps["clf"].coef_[0]
            vals = np.abs(coefs)
        return {f: float(v) for f, v in zip(self._features, vals)}

    def save(self, path: str) -> None:
        joblib.dump(
            {"estimator": self.estimator, "model": self._model,
             "features": self._features}, path)

    @classmethod
    def load(cls, path: str) -> "ChurnModel":
        blob = joblib.load(path)
        obj = cls.__new__(cls)
        obj.estimator = blob["estimator"]
        obj._model = blob["model"]
        obj._features = blob["features"]
        return obj
