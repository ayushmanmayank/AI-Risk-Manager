"""Loads the trained fraud model once at process startup and exposes it as
a singleton service (not per-request), plus the static reference statistics
used to approximate amount_zscore for single-transaction inference.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from src.models.explain import shap_explainer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
MODEL_VERSION = "fraud_model_v1"


class ModelService:
    """Singleton wrapper around the calibrated model bundle produced by
    src/models/train_fraud_model.py.
    """

    def __init__(self) -> None:
        self.model = None
        self.feature_columns: list[str] = []
        self.threshold: float = 0.5
        self.amount_reference_mean: float = 0.0
        self.amount_reference_std: float = 0.0
        self._loaded = False

    def load(self) -> None:
        """Load the model bundle and compute the amount_zscore reference stats.

        The reference mean/std is computed ONLY from the training slice
        (bundle['split_indices']['train_end']) of features.csv, never from
        validation or test rows, so this does not leak evaluation data into
        production inference.
        """
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Run src/models/train_fraud_model.py first."
            )
        bundle = joblib.load(MODEL_PATH)
        self.model = bundle["model"]
        self.feature_columns = list(bundle["feature_columns"])
        self.threshold = float(bundle.get("threshold", 0.5))

        if FEATURES_PATH.exists():
            train_end = bundle["split_indices"]["train_end"]
            history = (
                pd.read_csv(FEATURES_PATH, usecols=["Time", "Amount"])
                .sort_values("Time", kind="stable")
                .reset_index(drop=True)
            )
            training_amounts = history["Amount"].iloc[:train_end]
            self.amount_reference_mean = float(training_amounts.mean())
            self.amount_reference_std = float(training_amounts.std())

        shap_explainer.load(self.model, self.feature_columns)
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    def predict_proba(self, features: pd.DataFrame) -> float:
        """Return P(fraud) for a single-row feature DataFrame."""
        if not self.is_loaded:
            raise RuntimeError("Model is not loaded. Call ModelService.load() first.")
        return float(self.model.predict_proba(features[self.feature_columns])[:, 1][0])


# Process-wide singleton, loaded once from api/main.py's startup hook.
model_service = ModelService()
