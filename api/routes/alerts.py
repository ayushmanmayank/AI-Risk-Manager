"""GET /api/v1/alerts -- live fraud-rate spike status + persisted alert history."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.alerts import AlertEventOut, AlertsStatusOut
from api.services.anomaly_service import anomaly_service
from api.services.db import get_db
from api.services.db_models import AlertRecord

router = APIRouter()

RECENT_ALERTS_LIMIT = 10


@router.get("/alerts", response_model=AlertsStatusOut)
def get_alerts(db: Session = Depends(get_db)) -> AlertsStatusOut:
    result, window_oldest_timestamp = anomaly_service.current_status(db)

    first_detected_at = None
    if result.is_spike:
        first_detected_at = anomaly_service.ensure_alert_logged(db, result, window_oldest_timestamp)

    recent_alerts = db.execute(
        select(AlertRecord).order_by(AlertRecord.created_at.desc()).limit(RECENT_ALERTS_LIMIT)
    ).scalars().all()

    return AlertsStatusOut(
        is_spike_active=result.is_spike,
        anomaly_score=result.anomaly_score,
        current_fraud_rate=result.current_fraud_rate,
        baseline_fraud_rate=result.baseline_fraud_rate,
        severity=result.severity,
        window_size=result.window_size,
        insufficient_data=result.insufficient_data,
        first_detected_at=first_detected_at,
        recent_alerts=[AlertEventOut.model_validate(a) for a in recent_alerts],
    )
