"""DB lookups feeding src/evidence/evidence_engine.py's pure assembly logic."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api.services.db_models import ChargebackRecord, PredictionRecord, RefundRecord
from src.evidence.evidence_engine import EvidencePackage, build_evidence_package


def _prediction_to_dict(record: PredictionRecord) -> dict:
    return {
        "transaction_id": record.transaction_id,
        "time": record.time,
        "amount": record.amount,
        "fraud_probability": record.fraud_probability,
        "risk_tier": record.risk_tier,
        "decision": record.decision,
        "expected_loss": record.expected_loss,
        "model_version": record.model_version,
        "timestamp": record.timestamp,
        "shap_explanation": record.shap_explanation,
    }


def _refund_to_dict(record: RefundRecord) -> dict:
    return {
        "refund_id": record.refund_id,
        "transaction_id": record.transaction_id,
        "amount": record.amount,
        "timestamp": record.timestamp,
        "reason": record.reason,
    }


def _chargeback_to_dict(record: ChargebackRecord) -> dict:
    return {
        "chargeback_id": record.chargeback_id,
        "transaction_id": record.transaction_id,
        "reason": record.reason,
        "amount": record.amount,
        "timestamp": record.timestamp,
        "status": record.status,
    }


def get_evidence_package(db: Session, chargeback_id: str) -> EvidencePackage | None:
    """Returns None if no chargeback with this id exists. A missing
    transaction/refund is a normal, handled case inside build_evidence_package
    (not an error) -- only a missing chargeback itself is "not found" here.
    """
    chargeback_record = db.get(ChargebackRecord, chargeback_id)
    if chargeback_record is None:
        return None

    prediction_record = db.get(PredictionRecord, chargeback_record.transaction_id)
    refund_record = (
        db.query(RefundRecord).filter_by(transaction_id=chargeback_record.transaction_id).first()
    )

    return build_evidence_package(
        chargeback=_chargeback_to_dict(chargeback_record),
        transaction=_prediction_to_dict(prediction_record) if prediction_record else None,
        refund=_refund_to_dict(refund_record) if refund_record else None,
    )
