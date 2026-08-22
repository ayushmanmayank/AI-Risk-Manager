"""POST /api/v1/predict — score one transaction end to end."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.schemas.prediction import PredictionOut
from api.schemas.transaction import TransactionIn
from api.services.db import get_db
from api.services.db_models import PredictionRecord
from api.services.dedup import compute_content_hash
from api.services.feature_service import build_transaction_features
from api.services.model_service import model_service
from api.services.risk_service import evaluate_transaction
from src.models.explain import shap_explainer

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Identical content already scored; existing prediction returned unchanged"},
        409: {"description": "transaction_id already scored"},
        422: {"description": "Invalid input (missing field, wrong type, negative Amount, ...)"},
        503: {"description": "Model not loaded"},
    },
)
def predict(transaction: TransactionIn, response: Response, db: Session = Depends(get_db)) -> PredictionOut:
    if not model_service.is_loaded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model is not loaded")

    if transaction.transaction_id is not None:
        existing = db.get(PredictionRecord, transaction.transaction_id)
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"transaction_id '{transaction.transaction_id}' has already been scored",
            )

    payload = transaction.model_dump(exclude={"transaction_id"})
    content_hash = compute_content_hash(payload)

    # Content-hash fallback: only when the caller did NOT supply their own
    # transaction_id. An explicit id always creates its own row (see
    # api/services/dedup.py docstring) -- this only catches the case a
    # naive retry with no idempotency key would otherwise duplicate.
    if transaction.transaction_id is None:
        duplicate = db.scalar(
            select(PredictionRecord).where(PredictionRecord.content_hash == content_hash)
        )
        if duplicate is not None:
            response.status_code = status.HTTP_200_OK
            return PredictionOut.model_validate(duplicate)

    features = build_transaction_features(payload)
    fraud_probability = model_service.predict_proba(features)

    result = evaluate_transaction(
        transaction_id=transaction.transaction_id,
        amount=transaction.Amount,
        fraud_probability=fraud_probability,
    )

    top_positive, top_negative = shap_explainer.explain(features)

    record = PredictionRecord(
        transaction_id=result.transaction_id,
        time=transaction.Time,
        amount=transaction.Amount,
        fraud_probability=result.fraud_probability,
        risk_tier=result.risk_tier,
        decision=result.decision,
        expected_loss=result.expected_loss,
        model_version=result.model_version,
        timestamp=result.timestamp,
        top_positive_features=[vars(c) for c in top_positive],
        top_negative_features=[vars(c) for c in top_negative],
        content_hash=content_hash,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"transaction_id '{result.transaction_id}' already exists",
        )
    db.refresh(record)

    return PredictionOut.model_validate(record)
