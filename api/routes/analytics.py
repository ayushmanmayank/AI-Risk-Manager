"""GET /api/v1/analytics — aggregate stats over predictions made so far.

Honest limitation: "fraud rate among HIGH tier" would normally mean the
share of HIGH-tier transactions that were *actually* fraudulent. /predict
never receives a ground-truth Class label (it scores real, unlabeled
transactions), so no such ground truth exists to compute that against.

We deliberately do NOT fake this with fraud_probability >= threshold as a
substitute "rate": HIGH tier is itself defined as fraud_probability >=
high_threshold (0.70 by default), which already exceeds the model's 0.5
classification threshold, so that substitute would always read ~100% by
construction and would mislead rather than inform. high_tier_fraud_rate is
therefore always null for now, with a note explaining why, until a
feedback/labeling endpoint exists to record actual outcomes.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas.prediction import AnalyticsOut
from api.services.db import get_db
from api.services.db_models import PredictionRecord
from api.services.ttl_cache import TTLCache

router = APIRouter()

HIGH_TIER_FRAUD_RATE_NOTE = (
    "Not computable: /predict scores unlabeled transactions, so no ground-truth "
    "outcome exists yet for this endpoint. Requires a future feedback/labeling "
    "endpoint to populate confirmed fraud outcomes per transaction_id."
)

# Configurable via ANALYTICS_CACHE_TTL_SECONDS. Short on purpose: this
# endpoint backs the Dashboard, which users expect to reflect a just-sent
# prediction quickly -- see the Tier 4 report for the measured before/
# after this actually buys. A single cached value with no key is correct
# here because the response has no per-request parameters to vary by.
ANALYTICS_CACHE_TTL_SECONDS = float(os.environ.get("ANALYTICS_CACHE_TTL_SECONDS", "5"))
analytics_cache: TTLCache[AnalyticsOut] = TTLCache(ttl_seconds=ANALYTICS_CACHE_TTL_SECONDS)


def _compute_analytics(db: Session) -> AnalyticsOut:
    total = db.scalar(select(func.count()).select_from(PredictionRecord)) or 0

    tier_rows = db.execute(
        select(PredictionRecord.risk_tier, func.count()).group_by(PredictionRecord.risk_tier)
    ).all()
    count_by_risk_tier = {tier: count for tier, count in tier_rows}

    decision_rows = db.execute(
        select(PredictionRecord.decision, func.count()).group_by(PredictionRecord.decision)
    ).all()
    count_by_decision = {decision: count for decision, count in decision_rows}

    average_expected_loss = db.scalar(select(func.avg(PredictionRecord.expected_loss))) or 0.0

    return AnalyticsOut(
        total_transactions=total,
        count_by_risk_tier=count_by_risk_tier,
        count_by_decision=count_by_decision,
        average_expected_loss=float(average_expected_loss),
        high_tier_fraud_rate=None,
        high_tier_fraud_rate_note=HIGH_TIER_FRAUD_RATE_NOTE,
    )


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db)) -> AnalyticsOut:
    return analytics_cache.get(lambda: _compute_analytics(db))
