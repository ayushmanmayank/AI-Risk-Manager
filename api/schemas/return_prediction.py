"""Response schema for POST /api/v1/predict/return.

Deliberately smaller than PredictionOut: no decision/expected_loss fields,
because no cost model (false-positive vs false-negative return-handling
cost) was defined for this Tier 2 feature -- only return_probability was
asked for. risk_tier is a light-touch readability bucket on top of it,
not a cost-aware decision like the fraud model's ALLOW/REVIEW/HOLD.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReturnPredictionOut(BaseModel):
    order_id: str
    return_probability: float
    risk_tier: str  # LOW | MEDIUM | HIGH -- see src/risk/return_risk_tier.py
    model_version: str
    timestamp: datetime
