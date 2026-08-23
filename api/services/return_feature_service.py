"""Build the return-risk model's engineered feature row for a single
incoming order -- mirrors api/services/feature_service.py's pattern for
the fraud model.

Reuses src/features/build_return_features.py's add_country_dummies
directly (pure per-row) rather than duplicating it. customer/product
history are the return-model equivalent of amount_zscore's "approximated
with a static reference distribution" caveat: a live order has no rolling
history to compute from, so customer_order_count_so_far /
customer_return_rate_so_far / product_return_rate_so_far are looked up
from return_model_service's TRAINING-SLICE-ONLY reference stats instead
of recomputed causally -- an approximation of the true point-in-time
value, not identical to it. An unknown/new customer or product gets an
honest cold-start default (0 history / the training set's global average
return rate), never a guess.
"""

from __future__ import annotations

import pandas as pd

from api.services.return_model_service import return_model_service
from src.features.build_return_features import add_country_dummies


def build_order_features(order: dict) -> pd.DataFrame:
    """Turn a raw order dict (see api/schemas/return_order.py:ReturnOrderIn)
    into the exact feature row the return model expects, in the model's
    trained column order.
    """
    timestamp = order["order_timestamp"]
    row = pd.DataFrame(
        [
            {
                "Country": order["country"],
                "order_value": order["order_value"],
                "total_quantity": order["total_quantity"],
                "distinct_products": order["distinct_products"],
                "day_of_week": timestamp.weekday(),
                "month": timestamp.month,
                "hour_of_day": timestamp.hour,
            }
        ]
    )
    row = add_country_dummies(row)

    customer_id = order.get("customer_id")
    customer_entry = return_model_service.customer_stats.get(customer_id) if customer_id is not None else None
    if customer_entry is not None:
        row["customer_order_count_so_far"] = customer_entry["order_count"]
        row["customer_return_rate_so_far"] = customer_entry["return_rate"]
    else:
        # Honest cold start: unknown/guest customer, no prior history.
        row["customer_order_count_so_far"] = 0
        row["customer_return_rate_so_far"] = 0.0

    stock_codes = order.get("stock_codes") or []
    if stock_codes:
        rates = [
            return_model_service.product_stats.get(code, return_model_service.global_return_rate)
            for code in stock_codes
        ]
        row["product_return_rate_so_far"] = sum(rates) / len(rates)
    else:
        # No product info supplied -- fall back to the training set's
        # overall average rather than a guessed single-product value.
        row["product_return_rate_so_far"] = return_model_service.global_return_rate

    missing = [c for c in return_model_service.feature_columns if c not in row.columns]
    if missing:
        raise ValueError(f"Missing engineered feature columns: {missing}")
    return row[return_model_service.feature_columns]
