"""Day 2 step 5: sweep cost-minimizing thresholds on the validation set.

Loads the calibrated model saved by src/models/train_fraud_model.py,
regenerates its exact validation split from data/processed/features.csv,
scores it, and reports the expected-cost-minimizing threshold versus a
naive 0.5 threshold. Validation set only — test set is not touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    # Allow `python src/risk/run_threshold_sweep.py` (direct script execution,
    # consistent with the Day 1 scripts) in addition to
    # `python -m src.risk.run_threshold_sweep`.
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd

from src.risk.cost_engine import (
    best_threshold,
    confusion_counts_at_threshold,
    expected_cost,
    sweep_thresholds,
)
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
TARGET = "Class"

# Finer sweep than the DEFAULT_SWEEP_THRESHOLDS (0.1 steps) for a sharper
# cost-minimizing threshold estimate.
FINE_THRESHOLDS = tuple(round(t, 2) for t in np.arange(0.05, 0.96, 0.05))


def main() -> None:
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    split = bundle["split_indices"]

    data = pd.read_csv(FEATURES_PATH).sort_values("Time", kind="stable").reset_index(drop=True)
    validation_data = data.iloc[split["train_end"] : split["validation_end"]]

    x_validation = validation_data[feature_columns]
    y_validation = validation_data[TARGET].to_numpy()
    y_prob = model.predict_proba(x_validation)[:, 1]

    results = sweep_thresholds(y_validation, y_prob, thresholds=FINE_THRESHOLDS)
    best = best_threshold(results)

    naive_tp, naive_fp, naive_fn, naive_tn = confusion_counts_at_threshold(
        y_validation, y_prob, 0.5
    )
    naive_cost = expected_cost(naive_fp, naive_fn)

    print("=== Threshold Sweep (validation set only) ===")
    print(f"{'threshold':>9} | {'tp':>5} | {'fp':>5} | {'fn':>5} | {'tn':>7} | {'expected_cost':>14}")
    for r in results:
        marker = "  <-- min" if r.threshold == best.threshold else ""
        print(
            f"{r.threshold:>9.2f} | {r.tp:>5} | {r.fp:>5} | {r.fn:>5} | {r.tn:>7} | "
            f"{r.expected_cost:>14.2f}{marker}"
        )

    print()
    print("=== Comparison ===")
    print(
        f"Naive 0.50 threshold:        cost={naive_cost:.2f} "
        f"(tp={naive_tp}, fp={naive_fp}, fn={naive_fn}, tn={naive_tn})"
    )
    print(
        f"Cost-minimizing threshold {best.threshold:.2f}: cost={best.expected_cost:.2f} "
        f"(tp={best.tp}, fp={best.fp}, fn={best.fn}, tn={best.tn})"
    )
    if naive_cost > 0:
        savings_pct = (naive_cost - best.expected_cost) / naive_cost * 100
        print(f"Cost reduction vs naive 0.50: {naive_cost - best.expected_cost:.2f} ({savings_pct:.1f}%)")
    else:
        print("Naive cost is 0.00; no reduction possible.")


if __name__ == "__main__":
    main()
