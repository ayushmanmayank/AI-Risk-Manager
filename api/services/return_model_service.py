"""Loads the trained return-risk model once at process startup and exposes
it as a singleton service (not per-request) -- mirrors model_service.py's
pattern exactly, for a completely separate model/dataset/feature schema.

Also exposes the reference stats (customer/product historical return
rates, computed from the TRAINING slice only) needed for live
single-order feature engineering -- see return_feature_service.py and
train_return_model.py:build_reference_stats.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "return_model_v1.pkl"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "return_features.csv"
MODEL_VERSION = "return_model_v1"


class ReturnModelService:
    """Singleton wrapper around the calibrated model bundle produced by
    src/models/train_return_model.py.
    """

    def __init__(self) -> None:
        self.model = None
        self.feature_columns: list[str] = []
        self.threshold: float = 0.5
        self.customer_stats: dict[int, dict] = {}
        self.product_stats: dict[str, float] = {}
        self.global_return_rate: float = 0.0
        self._loaded = False

    def load(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Return model not found at {MODEL_PATH}. Run src/models/train_return_model.py first."
            )
        bundle = joblib.load(MODEL_PATH)
        self.model = bundle["model"]
        self.feature_columns = list(bundle["feature_columns"])
        self.threshold = float(bundle.get("threshold", 0.5))
        self.customer_stats = bundle.get("customer_stats", {})
        self.product_stats = bundle.get("product_stats", {})
        self.global_return_rate = float(bundle.get("global_return_rate", 0.0))
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    def predict_proba(self, features: pd.DataFrame) -> float:
        """Return P(returned) for a single-row feature DataFrame."""
        if not self.is_loaded:
            raise RuntimeError("Return model is not loaded. Call ReturnModelService.load() first.")
        return float(self.model.predict_proba(features[self.feature_columns])[:, 1][0])


# Process-wide singleton, loaded once from api/main.py's startup hook.
return_model_service = ReturnModelService()
