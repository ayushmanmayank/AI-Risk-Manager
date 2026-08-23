"""GET /api/v1/monitoring/drift -- training-vs-live feature drift report."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas.monitoring import DriftReportOut, FeatureDriftOut
from api.services.drift_service import drift_service
from api.services.db import get_db

router = APIRouter()


@router.get("/monitoring/drift", response_model=DriftReportOut)
def get_drift_report(db: Session = Depends(get_db)) -> DriftReportOut:
    report = drift_service.current_report(db)
    return DriftReportOut(
        overall_status=report.overall_status,
        features=[
            FeatureDriftOut(
                feature=f.feature,
                psi=f.psi,
                status=f.status,
                reference_sample_size=f.reference_sample_size,
                live_sample_size=f.live_sample_size,
            )
            for f in report.features
        ],
        live_sample_size=report.live_sample_size,
        min_live_sample_size=report.min_live_sample_size,
        insufficient_data=report.insufficient_data,
    )
