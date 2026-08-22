"""Precomputes real held-out TEST-SET evaluation metrics once at startup
for GET /api/v1/models.

Uses the TEST split specifically (validation_end onward), never
validation -- this is the one deliberate, already-audited (Day 5) look at
test. Recomputed here from the actual model bundle + features.csv rather
than hardcoded, so this page can never silently drift from what the
pipeline actually produces; if it ever disagreed with the Day 5 audit
numbers, that would mean something in the pipeline changed, which is
exactly the kind of drift worth surfacing, not hiding behind a constant.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from api.services.model_service import MODEL_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"

MODEL_NAME = "XGBoost Fraud Classifier (Platt-calibrated)"
DATASET_VERSION = "Kaggle mlg-ulb/creditcardfraud (creditcard.csv)"


class ModelInfoService:
    def __init__(self) -> None:
        self.info: dict | None = None

    def load(self) -> None:
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]
        split = bundle["split_indices"]
        threshold = float(bundle.get("threshold", 0.5))

        data = (
            pd.read_csv(FEATURES_PATH, usecols=[*feature_columns, "Class"])
            .sort_values("Time", kind="stable")
            .reset_index(drop=True)
        )
        test = data.iloc[split["validation_end"] :]

        y_true = test["Class"].to_numpy()
        y_prob = model.predict_proba(test[feature_columns])[:, 1]
        y_pred = (y_prob >= threshold).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

        self.info = {
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            # The currently-loaded model artifact's real filesystem mtime --
            # verifiable, not a fabricated narrative date.
            "training_date": datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, tz=timezone.utc),
            "dataset_version": DATASET_VERSION,
            "threshold": threshold,
            "precision": float(precision_score(y_true, y_pred)),
            "recall": float(recall_score(y_true, y_pred)),
            "f1": float(f1_score(y_true, y_pred)),
            "pr_auc": float(average_precision_score(y_true, y_prob)),
            "roc_auc": float(roc_auc_score(y_true, y_prob)),
            "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0,
            "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0,
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
            "test_set_size": int(len(test)),
        }

    @property
    def is_loaded(self) -> bool:
        return self.info is not None


# Process-wide singleton, loaded once from api/main.py's startup hook.
model_info_service = ModelInfoService()
