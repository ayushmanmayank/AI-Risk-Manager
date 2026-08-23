"""Combine a return probability with the risk-tier mapping -- return-model
equivalent of api/services/risk_service.py, minus a decision/expected-loss
engine (none was asked for; see api/routes/return_predict.py's docstring).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from api.services.return_model_service import MODEL_VERSION
from src.risk.return_risk_tier import risk_tier_for


@dataclass(frozen=True)
class ReturnPredictionResult:
    order_id: str
    return_probability: float
    risk_tier: str
    model_version: str
    timestamp: datetime


def generate_order_id() -> str:
    return f"order_{uuid.uuid4().hex}"


def evaluate_order(order_id: str | None, return_probability: float) -> ReturnPredictionResult:
    return ReturnPredictionResult(
        order_id=order_id or generate_order_id(),
        return_probability=return_probability,
        risk_tier=risk_tier_for(return_probability),
        model_version=MODEL_VERSION,
        timestamp=datetime.now(timezone.utc),
    )
