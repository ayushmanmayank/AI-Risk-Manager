"""Train and validate a temporally split, calibrated fraud classifier.

The final 15% of observations is deliberately not accessed by this script
beyond reserving its chronological boundary. It remains a Day 1 holdout set.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
TARGET = "Class"
RANDOM_STATE = 42


def temporal_boundaries(n_rows: int) -> tuple[int, int]:
    """Return exclusive endpoints for 70% train and 15% validation slices."""
    train_end = int(n_rows * 0.70)
    validation_end = int(n_rows * 0.85)
    return train_end, validation_end


def main() -> None:
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Features not found at {FEATURES_PATH}. Run build_features.py first."
        )

    data = pd.read_csv(FEATURES_PATH).sort_values("Time", kind="stable").reset_index(drop=True)
    train_end, validation_end = temporal_boundaries(len(data))
    feature_columns = [column for column in data.columns if column != TARGET]

    # Reserve the last 15% by index. Do not construct, inspect, or score it.
    development_data = data.iloc[:train_end]
    validation_data = data.iloc[train_end:validation_end]

    # Hold back the latest 15% of the development window for Platt calibration.
    fit_end = int(len(development_data) * 0.85)
    fit_data = development_data.iloc[:fit_end]
    calibration_data = development_data.iloc[fit_end:]

    x_fit, y_fit = fit_data[feature_columns], fit_data[TARGET]
    x_calibration, y_calibration = calibration_data[feature_columns], calibration_data[TARGET]
    x_validation, y_validation = validation_data[feature_columns], validation_data[TARGET]

    positives = int(y_fit.sum())
    negatives = int(len(y_fit) - positives)
    if positives == 0:
        raise ValueError("Training slice contains no fraud examples; cannot train classifier.")
    scale_pos_weight = negatives / positives

    base_model = XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    base_model.fit(x_fit, y_fit)

    # Platt scaling is fit only on the chronological calibration slice.
    calibrated_model = CalibratedClassifierCV(
        FrozenEstimator(base_model), method="sigmoid"
    )
    calibrated_model.fit(x_calibration, y_calibration)

    validation_probabilities = calibrated_model.predict_proba(x_validation)[:, 1]
    validation_predictions = (validation_probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y_validation, validation_predictions, labels=[0, 1])

    metrics = {
        "precision": precision_score(y_validation, validation_predictions, zero_division=0),
        "recall": recall_score(y_validation, validation_predictions, zero_division=0),
        "f1": f1_score(y_validation, validation_predictions, zero_division=0),
        "pr_auc": average_precision_score(y_validation, validation_probabilities),
        "roc_auc": roc_auc_score(y_validation, validation_probabilities),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": calibrated_model,
            "feature_columns": feature_columns,
            "threshold": 0.5,
            "split_indices": {
                "fit_end": fit_end,
                "train_end": train_end,
                "validation_end": validation_end,
                "test_start": validation_end,
            },
            "scale_pos_weight": scale_pos_weight,
            "validation_metrics": metrics,
            "validation_confusion_matrix": matrix.tolist(),
        },
        MODEL_PATH,
    )

    print("=== Temporal Split ===")
    print(f"Fit: 0 to {fit_end - 1:,} ({len(fit_data):,} rows; positives={int(y_fit.sum())})")
    print(
        f"Calibration: {fit_end:,} to {train_end - 1:,} "
        f"({len(calibration_data):,} rows; positives={int(y_calibration.sum())})"
    )
    print(
        f"Validation: {train_end:,} to {validation_end - 1:,} "
        f"({len(validation_data):,} rows; positives={int(y_validation.sum())})"
    )
    print(f"Test reserved, untouched: {validation_end:,} to {len(data) - 1:,}")
    print(f"scale_pos_weight: {scale_pos_weight:.2f}")
    print("=== Validation Metrics (threshold=0.50) ===")
    for name, value in metrics.items():
        print(f"{name}: {value:.6f}")
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(matrix)
    print(f"Saved calibrated model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
