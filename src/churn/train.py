import json
import os
import hashlib
from datetime import datetime, timezone

from src.mart import SalesMart
from src.churn.labeling import ChurnLabeler
from src.churn.features import SellerFeatureBuilder
from src.churn.model import ChurnModel
from src.churn.drift import DriftMonitor


def train_churn(db_path: str = "data/olist_mart.db",
                models_dir: str = "models",
                mart: SalesMart | None = None) -> dict:
    mart = mart or SalesMart(db_path)
    os.makedirs(models_dir, exist_ok=True)

    labeler = ChurnLabeler()
    cutoff = labeler.cutoff(mart)
    labels = labeler.label(mart)
    features = SellerFeatureBuilder().build(mart, cutoff)

    data = features.join(labels.set_index("seller_id"), how="inner")
    X = data[SellerFeatureBuilder.FEATURES]
    y = data["churned"]

    baseline = ChurnModel("logreg").fit(X, y)
    model = ChurnModel("xgboost").fit(X, y)

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_sellers": int(len(X)),
        "churn_rate": float(y.mean()),
        "dataset_hash": hashlib.sha256(
            X.to_csv().encode()).hexdigest()[:16],
        "baseline_logreg": baseline.evaluate(X, y),
        "xgboost": model.evaluate(X, y),
    }

    model.save(os.path.join(models_dir, "model.pkl"))
    with open(os.path.join(models_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(models_dir, "feature_importance.json"), "w",
              encoding="utf-8") as f:
        json.dump(model.feature_importance(), f, indent=2)
    DriftMonitor(X).save_reference(
        os.path.join(models_dir, "drift_reference.json"))
    return metrics


if __name__ == "__main__":
    m = train_churn()
    print(f"XGBoost AUC: {m['xgboost']['auc_roc']:.3f} | "
          f"baseline AUC: {m['baseline_logreg']['auc_roc']:.3f}")
