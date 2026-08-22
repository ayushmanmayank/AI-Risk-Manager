"""Response schema for GET /api/v1/alerts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: str
    alert_type: str
    severity: str
    description: str
    created_at: datetime


class AlertsStatusOut(BaseModel):
    is_spike_active: bool
    anomaly_score: float
    current_fraud_rate: float
    baseline_fraud_rate: float
    severity: str
    window_size: int
    insufficient_data: bool
    first_detected_at: datetime | None
    recent_alerts: list[AlertEventOut]
