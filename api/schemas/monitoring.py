"""Response schema for GET /api/v1/monitoring/drift."""

from __future__ import annotations

from pydantic import BaseModel


class FeatureDriftOut(BaseModel):
    feature: str
    psi: float
    status: str
    reference_sample_size: int
    live_sample_size: int


class DriftReportOut(BaseModel):
    overall_status: str
    features: list[FeatureDriftOut]
    live_sample_size: int
    min_live_sample_size: int
    insufficient_data: bool
