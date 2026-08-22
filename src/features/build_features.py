"""Build readable, time-aware features while retaining the raw PCA features."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
ROLLING_WINDOW = 10_000


def add_amount_log(data: pd.DataFrame) -> pd.Series:
    """log1p(Amount). Pure per-row function: no history or other rows needed.

    Safe to call on a single-row DataFrame at inference time.
    """
    return np.log1p(data["Amount"])


def add_hour_of_day(data: pd.DataFrame) -> pd.Series:
    """Hour-of-day derived from Time (seconds) modulo 86,400.

    Pure per-row function: no history or other rows needed. Safe to call on
    a single-row DataFrame at inference time.
    """
    return ((data["Time"] % 86_400) // 3_600).astype("int8")


def add_amount_zscore_batch(data: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.Series:
    """Rolling z-score of Amount using only strictly prior transactions.

    Requires `data` to already be sorted by Time ascending. Batch-only: needs
    a Time-ordered history, so it is not usable for scoring a single
    transaction in isolation (see amount_zscore_from_reference for that case).
    """
    prior_amounts = data["Amount"].shift(1)
    rolling_mean = prior_amounts.rolling(window, min_periods=1).mean()
    rolling_std = prior_amounts.rolling(window, min_periods=2).std()
    return (
        (data["Amount"] - rolling_mean) / rolling_std.replace(0, np.nan)
    ).fillna(0.0)


def amount_zscore_from_reference(
    amount: float, reference_mean: float, reference_std: float
) -> float:
    """Approximate amount_zscore for a single transaction with no live history.

    Simplifying assumption for real-time single-transaction inference (see
    api/services/feature_service.py): rather than a live rolling window of the
    prior 10,000 transactions (unavailable for a single incoming request), we
    use a static reference mean/std computed once from the training split.
    This is an approximation of the batch feature, not identical to it —
    document this whenever amount_zscore is read from an API response.
    """
    if reference_std == 0 or pd.isna(reference_std):
        return 0.0
    return (amount - reference_mean) / reference_std


def build_features(data: pd.DataFrame) -> pd.DataFrame:
    """Add interpretable amount and time features without removing raw columns.

    The rolling amount statistics use only prior transactions after ordering by
    Time, preventing future values from entering a transaction's z-score.
    """
    features = data.sort_values("Time", kind="stable").reset_index(drop=True).copy()
    features["amount_log"] = add_amount_log(features)
    features["hour_of_day"] = add_hour_of_day(features)
    features["amount_zscore"] = add_amount_zscore_batch(features)
    return features


def main() -> None:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {RAW_DATA_PATH}")

    data = pd.read_csv(RAW_DATA_PATH)
    features = build_features(data)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(features):,} rows and {len(features.columns)} columns to {OUTPUT_PATH}")
    print("Added: amount_log, hour_of_day, amount_zscore")


if __name__ == "__main__":
    main()
