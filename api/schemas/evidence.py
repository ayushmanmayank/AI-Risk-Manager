"""Schemas for GET /api/v1/chargebacks and GET /api/v1/chargebacks/{id}.

Chargeback/refund data is SEEDED/SIMULATED (see
src/evidence/seed_chargebacks.py); the transaction/prediction data it
references is real. See api/routes/chargebacks.py's DATA_MODEL_NOTE for
what this system does and doesn't have (no customer data; transaction and
risk_prediction are the same underlying record).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from api.schemas.prediction import PredictionOut


class ChargebackListItemOut(BaseModel):
    chargeback_id: str
    transaction_id: str
    reason: str
    amount: float
    timestamp: datetime
    status: str
    fraud_probability_at_scoring: float | None
    risk_tier_at_scoring: str | None
    was_flagged_in_advance: bool


class ChargebackDetailOut(BaseModel):
    chargeback_id: str
    transaction_id: str
    reason: str
    amount: float
    timestamp: datetime
    status: str


class RefundOut(BaseModel):
    refund_id: str
    transaction_id: str
    amount: float
    timestamp: datetime
    reason: str


class TimelineEventOut(BaseModel):
    event: str
    timestamp: datetime | None
    description: str


class EvidenceSummaryOut(BaseModel):
    was_flagged_in_advance: bool
    risk_tier_at_scoring: str | None
    decision_at_scoring: str | None
    fraud_probability_at_scoring: float | None
    narrative: str


class EvidencePackageOut(BaseModel):
    chargeback: ChargebackDetailOut
    transaction: PredictionOut | None
    # Same underlying record as `transaction` in this system -- exposed as
    # its own field to match the spec's named lookup chain, not a second
    # independent source. See DATA_MODEL_NOTE.
    risk_prediction: PredictionOut | None
    customer: str
    refund: RefundOut | None
    timeline: list[TimelineEventOut]
    summary: EvidenceSummaryOut
    data_model_note: str
