"""POST /api/v1/simulate -- re-threshold the model's precomputed
VALIDATION-set probabilities (see api/services/simulation_service.py) to
show the precision/recall/cost tradeoff at any threshold, live. Reuses
src/risk/cost_engine.py verbatim (Day 2); no new ML logic here.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.schemas.simulate import SimulateRequest, SimulateResponse
from api.services.simulation_service import simulation_service
from src.risk.cost_engine import confusion_counts_at_threshold, expected_cost

router = APIRouter()


@router.post("/simulate", response_model=SimulateResponse)
def simulate(request: SimulateRequest) -> SimulateResponse:
    if not simulation_service.is_loaded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Validation set not loaded")

    tp, fp, fn, tn = confusion_counts_at_threshold(
        simulation_service.y_true, simulation_service.y_prob, request.threshold
    )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    actual_fraud_count = tp + fn
    fraud_caught_percent = (tp / actual_fraud_count * 100) if actual_fraud_count > 0 else 0.0

    total = tp + fp + fn + tn
    transactions_affected_count = tp + fp
    transactions_affected_percent = (transactions_affected_count / total * 100) if total > 0 else 0.0

    financial_loss = expected_cost(fp, fn, request.false_positive_cost, request.false_negative_cost)

    return SimulateResponse(
        threshold=request.threshold,
        false_positive_cost=request.false_positive_cost,
        false_negative_cost=request.false_negative_cost,
        precision=precision,
        recall=recall,
        false_positive_rate=false_positive_rate,
        fraud_caught_count=tp,
        fraud_caught_percent=fraud_caught_percent,
        transactions_affected_count=transactions_affected_count,
        transactions_affected_percent=transactions_affected_percent,
        expected_financial_loss=financial_loss,
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        validation_set_size=total,
    )
