"""SHAP TreeExplainer for the trained XGBoost fraud model.

Important caveat, stated once here and referenced elsewhere: SHAP explains
the BASE XGBoost model's raw margin (log-odds) output, not the calibrated
probability that /predict actually returns (see train_fraud_model.py --
Platt/sigmoid calibration is fit on top of the base model). Sigmoid
calibration is a monotonic transform of that raw score, so the DIRECTION
and RELATIVE RANKING of each feature's contribution still holds for the
calibrated probability -- but the SHAP values themselves live in log-odds
space, not "probability points." Never present them as the latter.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap

# Human-readable labels for the engineered features. V1-V28 are PCA
# components from the original Kaggle dataset with no known real-world
# meaning -- we label them as anonymized signals rather than inventing
# fake semantics for them.
FEATURE_LABELS: dict[str, str] = {
    "amount_log": "Transaction amount (log-scaled)",
    "hour_of_day": "Hour of day",
    "amount_zscore": "Amount vs. recent spending pattern",
    "Time": "Time since first transaction in the dataset",
    "Amount": "Transaction amount",
}


def label_for(feature: str) -> str:
    if feature in FEATURE_LABELS:
        return FEATURE_LABELS[feature]
    if feature.startswith("V") and feature[1:].isdigit():
        return f"Anonymized signal {feature}"
    return feature


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    label: str
    shap_value: float
    feature_value: float


def unwrap_base_estimator(calibrated_model):
    """Reach through CalibratedClassifierCV(FrozenEstimator(XGBClassifier))
    to the fitted XGBClassifier SHAP's TreeExplainer needs direct tree
    access to -- see train_fraud_model.py for how the bundle is built.
    """
    try:
        return calibrated_model.calibrated_classifiers_[0].estimator.estimator
    except (AttributeError, IndexError) as exc:
        raise TypeError(
            "Expected a fitted CalibratedClassifierCV(FrozenEstimator(XGBClassifier)); "
            f"got {type(calibrated_model)}"
        ) from exc


class ShapExplainer:
    """Loads a single TreeExplainer once and reuses it across requests."""

    def __init__(self) -> None:
        self._explainer: shap.TreeExplainer | None = None
        self.feature_columns: list[str] = []

    def load(self, calibrated_model, feature_columns: list[str]) -> None:
        base_model = unwrap_base_estimator(calibrated_model)
        self._explainer = shap.TreeExplainer(base_model)
        self.feature_columns = list(feature_columns)

    @property
    def is_loaded(self) -> bool:
        return self._explainer is not None

    def explain(
        self, features: pd.DataFrame, top_n: int = 5
    ) -> tuple[list[FeatureContribution], list[FeatureContribution]]:
        """Return (top_positive, top_negative) contributions for one row.

        Positive SHAP values push the raw score toward fraud; negative
        values push it toward legitimate. Both lists are sorted by
        magnitude (largest push first) and capped at top_n.
        """
        if self._explainer is None:
            raise RuntimeError("ShapExplainer is not loaded. Call load() first.")

        ordered = features[self.feature_columns]
        shap_values = np.asarray(self._explainer.shap_values(ordered))[0]
        row = ordered.iloc[0]

        contributions = [
            FeatureContribution(
                feature=col,
                label=label_for(col),
                shap_value=float(shap_values[i]),
                feature_value=float(row[col]),
            )
            for i, col in enumerate(self.feature_columns)
        ]

        top_positive = sorted(
            (c for c in contributions if c.shap_value > 0),
            key=lambda c: c.shap_value,
            reverse=True,
        )[:top_n]
        top_negative = sorted(
            (c for c in contributions if c.shap_value < 0),
            key=lambda c: c.shap_value,
        )[:top_n]
        return top_positive, top_negative


# Process-wide singleton, loaded once alongside the model (see
# api/services/model_service.py).
shap_explainer = ShapExplainer()
