"""Input schema for POST /api/v1/predict/return.

Unlike TransactionIn (which matches the fraud model's training data shape
exactly -- raw Time/Amount/V1-V28), this schema takes the natural,
order-level fields a real checkout/OMS would have at order-placement
time. Server-side feature engineering (day_of_week/month/hour_of_day from
order_timestamp, customer/product history lookups) happens in
api/services/return_feature_service.py -- see that module for exactly
what's derived and what's approximated for a single live order versus the
full causal history in data/processed/return_features.csv.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReturnOrderIn(BaseModel):
    order_id: str | None = Field(
        default=None, description="Client-supplied id; a UUID is generated if omitted."
    )
    customer_id: int | None = Field(
        default=None,
        description=(
            "None means an unknown/guest customer -- scored with no customer history "
            "(an honest cold start, not a guess; see return_feature_service.py)."
        ),
    )
    country: str = Field(..., description="Shipping/billing country, e.g. 'United Kingdom'.")
    order_value: float = Field(..., gt=0, description="Total order value in the same currency as training.")
    total_quantity: int = Field(..., gt=0, description="Total units across all line items in the order.")
    distinct_products: int = Field(..., ge=1, description="Number of distinct products in the order.")
    stock_codes: list[str] = Field(
        default_factory=list,
        description=(
            "Optional product codes in the order, used for product-history lookup. Empty list "
            "falls back to the training set's global average return rate (see "
            "return_model_service.py's reference_stats)."
        ),
    )
    order_timestamp: datetime | None = Field(
        default=None, description="Defaults to now() if omitted."
    )
