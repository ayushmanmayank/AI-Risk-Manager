"""Input schema for POST /api/v1/predict — matches the training data shape
(Time, Amount, V1-V28) exactly, so no feature is silently defaulted.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, create_model

_V_COLUMN_FIELDS = {
    f"V{i}": (float, Field(..., description=f"PCA-anonymized component V{i}."))
    for i in range(1, 29)
}

TransactionIn = create_model(
    "TransactionIn",
    __base__=BaseModel,
    transaction_id=(
        Optional[str],
        Field(default=None, description="Client-supplied id; a UUID is generated if omitted."),
    ),
    Time=(
        float,
        Field(..., ge=0, description="Seconds elapsed since the first transaction in the dataset."),
    ),
    Amount=(float, Field(..., ge=0, description="Transaction amount; must be non-negative.")),
    **_V_COLUMN_FIELDS,
)
