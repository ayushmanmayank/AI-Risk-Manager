"""POST /api/v1/predict — score one transaction end to end."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
from api.services.rate_limiter import RateLimiter
from api.services.risk_service import evaluate_transaction
from src.models.explain import shap_explainer

router = APIRouter()

# Configurable via PREDICT_RATE_LIMIT_PER_MINUTE (requests/minute per
# client IP) -- see api/services/rate_limiter.py for the algorithm and
# why it's hand-rolled rather than a library.
#
# 200/min, not the more obvious-looking "60/min" -- found live, not
# assumed: scripts/reset_demo_data.py legitimately sends
# BASELINE_HIGH_COUNT + BASELINE_NORMAL_COUNT + COOLDOWN_COUNT = 3 + 15 +
# 50 = 68 real /predict calls in a single run, by design (see that
# script's own docstring), and it's meant to be safe to run before every
# rehearsal, back-to-back. Two consecutive runs -- exactly what
# tests/test_reset_script.py's idempotency test does, and what a judge
# re-running it between takes would do too -- is 136 calls, which a
# 60/min default would partially reject. 200/min comfortably covers that
# with real margin (even reset + a full simulate.py demo burst in the
# same minute stays under it) while still capping a genuinely runaway
# client loop at a small fraction of what an actual abusive script would
# attempt.
PREDICT_RATE_LIMIT_PER_MINUTE = int(os.environ.get("PREDICT_RATE_LIMIT_PER_MINUTE", "200"))
predict_rate_limiter = RateLimiter(max_requests=PREDICT_RATE_LIMIT_PER_MINUTE, window_seconds=60.0)


def enforce_predict_rate_limit(request: Request) -> None:
    """FastAPI dependency: rejects with 429 once the calling IP exceeds
    the configured budget. A dependency (not middleware) so it stays
    scoped to this one endpoint -- other routes are intentionally
    unaffected, since /predict is the one endpoint a runaway client loop
    would actually hammer.
    """
    # request.client is None only in contexts with no real client
    # connection (some test harnesses) -- fall back to a fixed key rather
    # than crashing; every such caller then shares one budget, which is
    # fine since it's not a real multi-client scenario.
    client_key = request.client.host if request.client else "unknown"
    result = predict_rate_limiter.check(client_key)
    if not result.allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: max {PREDICT_RATE_LIMIT_PER_MINUTE} requests/minute "
                f"per client. Retry after {result.retry_after_seconds:.1f}s."
            ),
            headers={"Retry-After": str(int(result.retry_after_seconds) + 1)},
        )


@router.post(
    "/predict",
    response_model=PredictionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Identical content already scored; existing prediction returned unchanged"},
        409: {"description": "transaction_id already scored"},
        422: {"description": "Invalid input (missing field, wrong type, negative Amount, ...)"},
        429: {"description": "Rate limit exceeded for this client IP"},
        503: {"description": "Model not loaded"},
    },
    dependencies=[Depends(enforce_predict_rate_limit)],
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
