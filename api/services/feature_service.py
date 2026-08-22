"""Build the model's engineered feature row for a single incoming transaction.

Reuses src/features/build_features.py's per-row functions directly rather
than duplicating the amount_log / hour_of_day logic. amount_zscore is the
one exception: the batch version needs a Time-ordered rolling window of
prior transactions, which a single API request does not have, so it is
approximated with a static reference distribution instead (see
amount_zscore_from_reference's docstring for the caveat).
"""

from __future__ import annotations

import pandas as pd

from api.services.model_service import model_service
from src.features.build_features import (
    add_amount_log,
    add_hour_of_day,
    amount_zscore_from_reference,
)


def build_transaction_features(transaction: dict) -> pd.DataFrame:
    """Turn a raw transaction dict (Time, Amount, V1-V28) into the exact
    feature row the model expects, in the model's trained column order.
    """
    row = pd.DataFrame([transaction])
    row["amount_log"] = add_amount_log(row)
    row["hour_of_day"] = add_hour_of_day(row)
    row["amount_zscore"] = amount_zscore_from_reference(
        row["Amount"].iloc[0],
        model_service.amount_reference_mean,
        model_service.amount_reference_std,
    )

    missing = [c for c in model_service.feature_columns if c not in row.columns]
    if missing:
        raise ValueError(f"Missing engineered feature columns: {missing}")
    return row[model_service.feature_columns]
