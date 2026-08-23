"""POST /api/v1/predict/return -- score one order's return risk.

Separate endpoint from POST /api/v1/predict, deliberately, not an added
field on the fraud endpoint's response. Reasons:
1. Completely different input schema -- the fraud model needs raw
   Time/Amount/V1-V28 (ULB dataset columns); the return model needs
   order_value/country/customer history (Online Retail II-derived
   columns). Cramming both into one request body would mean either two
   unrelated sets of required fields on every fraud /predict call, or a
   confusing "send fraud fields OR return fields OR both" contract.
2. Two independent models, two independent datasets, two independent
   training pipelines -- REST-wise these are two different resources
   being scored, not one enriched resource.
3. Keeps the existing, already-tested /predict contract (used by
   simulator/simulate.py, scripts/reset_demo_data.py, the dashboard, etc.)
   completely unchanged -- zero risk of a Tier 2 addition regressing
   Tier 1/original behavior.

Stateless: unlike /predict, this does NOT persist scored orders to the
database. The Model Performance display for this model (Tier 2) shows
real held-out TEST-SET metrics (see return_model_info_service.py),
not live-traffic counts -- there was no ask for a return-order Dashboard
history, only for the model's own evaluation metrics to be shown, so no
new table/aggregation was built for that beyond what's needed here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from api.schemas.return_order import ReturnOrderIn
from api.schemas.return_prediction import ReturnPredictionOut
from api.services.return_feature_service import build_order_features
from api.services.return_model_service import return_model_service
from api.services.return_risk_service import evaluate_order

router = APIRouter()


@router.post(
    "/predict/return",
    response_model=ReturnPredictionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"description": "Invalid input (missing field, wrong type, non-positive order_value, ...)"},
        503: {"description": "Return model not loaded"},
    },
)
def predict_return(order: ReturnOrderIn) -> ReturnPredictionOut:
    if not return_model_service.is_loaded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Return model is not loaded")

    payload = order.model_dump()
    payload["order_timestamp"] = payload["order_timestamp"] or datetime.now(timezone.utc)

    features = build_order_features(payload)
    return_probability = return_model_service.predict_proba(features)

    result = evaluate_order(order_id=order.order_id, return_probability=return_probability)
    return ReturnPredictionOut(
        order_id=result.order_id,
        return_probability=result.return_probability,
        risk_tier=result.risk_tier,
        model_version=result.model_version,
        timestamp=result.timestamp,
    )
