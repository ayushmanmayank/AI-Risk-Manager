"""Combine a fraud probability with the Day 2 decision + expected-loss engines."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from api.services.model_service import MODEL_VERSION
from src.risk.decision_engine import (
    DEFAULT_HIGH_THRESHOLD,
    DEFAULT_MEDIUM_THRESHOLD,
    decide,
)


@dataclass(frozen=True)
class PredictionResult:
    transaction_id: str
    fraud_probability: float
    risk_tier: str
    decision: str
    expected_loss: float
    model_version: str
    timestamp: datetime


def generate_transaction_id() -> str:
    return f"txn_{uuid.uuid4().hex}"


def evaluate_transaction(
    transaction_id: str | None,
    amount: float,
    fraud_probability: float,
    medium_threshold: float = DEFAULT_MEDIUM_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
) -> PredictionResult:
    """Score a transaction's decision using the Day 2 risk engine."""
    decision = decide(
        fraud_probability=fraud_probability,
        transaction_amount=amount,
        medium_threshold=medium_threshold,
        high_threshold=high_threshold,
    )
    return PredictionResult(
        transaction_id=transaction_id or generate_transaction_id(),
        fraud_probability=fraud_probability,
        risk_tier=decision.risk_tier,
        decision=decision.decision,
        expected_loss=decision.expected_loss,
        model_version=MODEL_VERSION,
        timestamp=datetime.now(timezone.utc),
    )
