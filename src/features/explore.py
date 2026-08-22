"""Validate and summarize the raw Kaggle credit-card-fraud dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
EXPECTED_COLUMNS = {"Time", "Amount", "Class", *[f"V{i}" for i in range(1, 29)]}


def load_and_validate(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the dataset and fail early if its expected schema is absent."""
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Place creditcard.csv in data/raw/."
        )

    data = pd.read_csv(path)
    missing = EXPECTED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return data


def print_summary(data: pd.DataFrame) -> None:
    """Print the Day 1 validation and exploration summary."""
    class_counts = data["Class"].value_counts().sort_index()
    non_fraud = int(class_counts.get(0, 0))
    fraud = int(class_counts.get(1, 0))
    fraud_rate = fraud / len(data) if len(data) else 0.0
    imbalance_ratio = non_fraud / fraud if fraud else float("inf")

    print("=== Credit Card Fraud Dataset Summary ===")
    print(f"Rows: {len(data):,}")
    print(f"Columns: {len(data.columns)}")
    print(f"Null values: {int(data.isna().sum().sum()):,}")
    print(f"Duplicate rows: {int(data.duplicated().sum()):,}")
    print("Class counts:")
    print(f"  Non-fraud (0): {non_fraud:,}")
    print(f"  Fraud (1): {fraud:,}")
    print(f"Fraud rate: {fraud_rate:.4%}")
    print(f"Non-fraud : fraud ratio: {imbalance_ratio:.2f}:1")
    print(f"Time range (seconds): {data['Time'].min():.0f} to {data['Time'].max():.0f}")
    print(f"Amount range: {data['Amount'].min():.2f} to {data['Amount'].max():.2f}")


if __name__ == "__main__":
    print_summary(load_and_validate())
