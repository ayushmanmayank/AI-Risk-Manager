"""GET /api/v1/chargebacks and GET /api/v1/chargebacks/{id} -- chargeback
evidence responder (Day 11), with an automated narrative summary (Tier 1,
feature/chargeback-llm-summary) layered on top of the detail response --
see src/evidence/summarize_evidence.py. Despite the branch name, this is
a pure Python template over already-assembled evidence fields, not an
LLM call -- no external API, no API key.

Chargeback/refund data is SEEDED/SIMULATED (see
src/evidence/seed_chargebacks.py) -- there is no real chargeback history.
The transaction/prediction data each chargeback is layered onto is real
(replayed historical transactions or manual /predict calls), never
fabricated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.evidence import ChargebackListItemOut, EvidencePackageOut
from api.schemas.prediction import PredictionOut
from api.services.db import get_db
from api.services.db_models import ChargebackRecord, PredictionRecord
from api.services.evidence_service import get_evidence_package
from src.evidence.summarize_evidence import generate_summary

router = APIRouter()

DATA_MODEL_NOTE = (
    "This system has no separate transactions or customer table. "
    "'transaction' and 'risk_prediction' below are the SAME underlying "
    "record (the prediction row written at /predict time holds both the "
    "transaction's own fields and the model's risk assessment). "
    "'customer' is always 'not available' -- no customer data model exists."
)


@router.get("/chargebacks", response_model=list[ChargebackListItemOut])
def list_chargebacks(db: Session = Depends(get_db)) -> list[ChargebackListItemOut]:
    chargebacks = (
        db.execute(select(ChargebackRecord).order_by(ChargebackRecord.timestamp.desc())).scalars().all()
    )
    items: list[ChargebackListItemOut] = []
    for chargeback in chargebacks:
        prediction = db.get(PredictionRecord, chargeback.transaction_id)
        items.append(
            ChargebackListItemOut(
                chargeback_id=chargeback.chargeback_id,
                transaction_id=chargeback.transaction_id,
                reason=chargeback.reason,
                amount=chargeback.amount,
                timestamp=chargeback.timestamp,
                status=chargeback.status,
                fraud_probability_at_scoring=prediction.fraud_probability if prediction else None,
                risk_tier_at_scoring=prediction.risk_tier if prediction else None,
                was_flagged_in_advance=(prediction.decision != "ALLOW") if prediction else False,
            )
        )
    return items


@router.get("/chargebacks/{chargeback_id}", response_model=EvidencePackageOut)
def get_chargeback_evidence(chargeback_id: str, db: Session = Depends(get_db)) -> EvidencePackageOut:
    package = get_evidence_package(db, chargeback_id)
    if package is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"chargeback_id '{chargeback_id}' not found")

    transaction_out = PredictionOut.model_validate(package.transaction) if package.transaction else None
    auto_summary = generate_summary(package)

    return EvidencePackageOut(
        chargeback={
            "chargeback_id": package.chargeback["chargeback_id"],
            "transaction_id": package.chargeback["transaction_id"],
            "reason": package.chargeback["reason"],
            "amount": package.chargeback["amount"],
            "timestamp": package.chargeback["timestamp"],
            "status": package.chargeback["status"],
        },
        transaction=transaction_out,
        risk_prediction=transaction_out,
        customer=package.customer,
        refund=package.refund,
        timeline=[
            {"event": e.event, "timestamp": e.timestamp, "description": e.description} for e in package.timeline
        ],
        summary={
            "was_flagged_in_advance": package.summary.was_flagged_in_advance,
            "risk_tier_at_scoring": package.summary.risk_tier_at_scoring,
            "decision_at_scoring": package.summary.decision_at_scoring,
            "fraud_probability_at_scoring": package.summary.fraud_probability_at_scoring,
            "narrative": package.summary.narrative,
        },
        auto_summary={
            "text": auto_summary.text,
            "available": auto_summary.available,
            "error": auto_summary.error,
        },
        data_model_note=DATA_MODEL_NOTE,
    )
