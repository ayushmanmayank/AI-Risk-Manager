"""Train and validate a temporally split, calibrated return-risk
classifier -- the Tier 2 "return-risk scorer" named in the hackathon
brief's examples.

Mirrors src/models/train_fraud_model.py's methodology exactly (same
70/15/15 temporal split shape, same fit/calibration split within the
training window, same XGBoost + Platt-calibration approach, same metric
set) so the two models are directly comparable in rigor -- see this
project's README "Known Limitations" for the one place they are NOT
comparable: dataset size, maturity, and label precision (see
src/features/build_return_features.py's module docstring for the label
construction caveat).

The final 15% of observations is deliberately not accessed by this
script beyond reserving its chronological boundary, same as the fraud
model's holdout discipline.
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
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "return_features.csv"
PRODUCTS_PATH = PROJECT_ROOT / "data" / "processed" / "return_features_products.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "return_model_v1.pkl"
TARGET = "returned"
NON_FEATURE_COLUMNS = {"Invoice", "CustomerID", "InvoiceDate", "Country", TARGET}
RANDOM_STATE = 42


def temporal_boundaries(n_rows: int) -> tuple[int, int]:
    """Return exclusive endpoints for 70% train and 15% validation slices --
    identical shape to train_fraud_model.py's split.
    """
    train_end = int(n_rows * 0.70)
    validation_end = int(n_rows * 0.85)
    return train_end, validation_end


def build_reference_stats(
    orders: pd.DataFrame, products: pd.DataFrame, train_end: int
) -> dict:
    """Reference stats for LIVE single-order inference (see
    api/services/return_feature_service.py), computed ONLY from the
    training slice -- same "no leakage into live approximation" discipline
    as model_service.py's amount_reference_mean/std for the fraud model.

    customer_stats: {customer_id: {order_count, return_rate}} as observed
    across the training slice (a customer's full history there, not a
    point-in-time causal snapshot -- this is the same kind of
    approximation amount_zscore_from_reference already makes: a static
    reference substituting for genuinely live history).
    product_stats: {stock_code: return_rate} likewise, from the
    training-slice's product-level occurrences.
    global_return_rate: fallback for a customer/product never seen in
    training -- an honest "no prior signal" default, not a guess.
    """
    training_orders = orders.iloc[:train_end]
    training_cutoff_date = training_orders["InvoiceDate"].max()

    customer_groups = training_orders.groupby("CustomerID")[TARGET].agg(["count", "mean"])
    customer_stats = {
        int(customer_id): {"order_count": int(row["count"]), "return_rate": float(row["mean"])}
        for customer_id, row in customer_groups.iterrows()
    }

    training_products = products[products["InvoiceDate"] <= training_cutoff_date]
    product_groups = training_products.groupby("StockCode")[TARGET].mean()
    product_stats = {code: float(rate) for code, rate in product_groups.items()}

    return {
        "customer_stats": customer_stats,
        "product_stats": product_stats,
        "global_return_rate": float(training_orders[TARGET].mean()),
    }


def main() -> None:
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Features not found at {FEATURES_PATH}. Run build_return_features.py first."
        )
    if not PRODUCTS_PATH.exists():
        raise FileNotFoundError(
            f"Product table not found at {PRODUCTS_PATH}. Run build_return_features.py first."
        )

    data = pd.read_csv(FEATURES_PATH, parse_dates=["InvoiceDate"]).sort_values(
        "InvoiceDate", kind="stable"
    ).reset_index(drop=True)
    products = pd.read_csv(PRODUCTS_PATH, parse_dates=["InvoiceDate"])

    train_end, validation_end = temporal_boundaries(len(data))
    feature_columns = [c for c in data.columns if c not in NON_FEATURE_COLUMNS]

    development_data = data.iloc[:train_end]
    validation_data = data.iloc[train_end:validation_end]

    fit_end = int(len(development_data) * 0.85)
    fit_data = development_data.iloc[:fit_end]
    calibration_data = development_data.iloc[fit_end:]

    x_fit, y_fit = fit_data[feature_columns], fit_data[TARGET]
    x_calibration, y_calibration = calibration_data[feature_columns], calibration_data[TARGET]
    x_validation, y_validation = validation_data[feature_columns], validation_data[TARGET]

    positives = int(y_fit.sum())
    negatives = int(len(y_fit) - positives)
    if positives == 0:
        raise ValueError("Training slice contains no returned examples; cannot train classifier.")
    scale_pos_weight = negatives / positives

    base_model = XGBClassifier(
        n_estimators=300,
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

    calibrated_model = CalibratedClassifierCV(FrozenEstimator(base_model), method="sigmoid")
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

    reference_stats = build_reference_stats(data, products, train_end)

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
            **reference_stats,
        },
        MODEL_PATH,
    )

    print("=== Temporal Split (by InvoiceDate) ===")
    print(f"Fit: 0 to {fit_end - 1:,} ({len(fit_data):,} rows; returned={int(y_fit.sum())})")
    print(
        f"Calibration: {fit_end:,} to {train_end - 1:,} "
        f"({len(calibration_data):,} rows; returned={int(y_calibration.sum())})"
    )
    print(
        f"Validation: {train_end:,} to {validation_end - 1:,} "
        f"({len(validation_data):,} rows; returned={int(y_validation.sum())})"
    )
    print(f"Test reserved, untouched: {validation_end:,} to {len(data) - 1:,}")
    print(f"scale_pos_weight: {scale_pos_weight:.2f}")
    print("=== Validation Metrics (threshold=0.50) ===")
    for name, value in metrics.items():
        print(f"{name}: {value:.6f}")
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(matrix)
    print(f"Reference stats: {len(reference_stats['customer_stats']):,} customers, "
          f"{len(reference_stats['product_stats']):,} products, "
          f"global_return_rate={reference_stats['global_return_rate']:.4f}")
    print(f"Saved calibrated model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
