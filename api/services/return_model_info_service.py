"""Precomputes real held-out TEST-SET evaluation metrics once at startup
for GET /api/v1/models/return -- return-model equivalent of
model_info_service.py.

Same discipline: recomputed here from the actual model bundle + the
return-features table, never hardcoded, so this can't silently drift from
what the pipeline actually produces.

DATASET_HONESTY_NOTE exists because this model's dataset and label are
genuinely less rigorous than the fraud model's ULB dataset -- see
src/features/build_return_features.py's module docstring for exactly
why (the return/cancellation label is a structural proxy, not a confirmed
ground truth, and can over-attribute a returned order backward across a
customer's earlier orders of the same product). This note is surfaced
directly in the API response, not just in code comments, per this
project's "state limitations where they're seen, not just where they're
written" convention (compare: DATA_MODEL_NOTE on the chargebacks
endpoint).
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

from api.services.return_model_service import MODEL_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "return_model_v1.pkl"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "return_features.csv"

MODEL_NAME = "XGBoost Return-Risk Classifier (Platt-calibrated)"
DATASET_VERSION = "UCI Online Retail II (archive.ics.uci.edu/dataset/502)"
DATASET_HONESTY_NOTE = (
    "This model is trained on a smaller, less-established dataset than the fraud model's "
    "ULB/Kaggle dataset (30K labeled orders vs 284.8K labeled transactions), and its "
    "'returned' label is a derived proxy -- a customer's later cancellation invoice sharing "
    "a product with this order -- not a confirmed, audited ground truth. It can also "
    "over-attribute risk backward across a customer's earlier orders of a repeatedly "
    "purchased product, and a 90-day maturation cutoff was applied to reduce (not fully "
    "eliminate) right-censoring bias near the dataset's end date. Treat these metrics with "
    "more caution than the fraud model's."
)


class ReturnModelInfoService:
    def __init__(self) -> None:
        self.info: dict | None = None

    def load(self) -> None:
        # No existence check here, same as model_info_service.py: by the
        # time api/main.py's lifespan reaches this call,
        # return_model_service.load() has already run and would have
        # raised loudly on a missing model file -- this never executes
        # against a genuinely absent bundle.
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]
        split = bundle["split_indices"]
        threshold = float(bundle.get("threshold", 0.5))

        data = (
            pd.read_csv(FEATURES_PATH, usecols=[*feature_columns, "InvoiceDate", "returned"], parse_dates=["InvoiceDate"])
            .sort_values("InvoiceDate", kind="stable")
            .reset_index(drop=True)
        )
        test = data.iloc[split["validation_end"] :]

        y_true = test["returned"].to_numpy()
        y_prob = model.predict_proba(test[feature_columns])[:, 1]
        y_pred = (y_prob >= threshold).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

        self.info = {
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "training_date": datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, tz=timezone.utc),
            "dataset_version": DATASET_VERSION,
            "dataset_honesty_note": DATASET_HONESTY_NOTE,
            "threshold": threshold,
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
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
return_model_info_service = ReturnModelInfoService()
