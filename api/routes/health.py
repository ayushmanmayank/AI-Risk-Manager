"""GET /api/v1/health — confirms the model is loaded and the DB is reachable."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.schemas.prediction import HealthOut
from api.services.db import DB_PATH, PROJECT_ROOT, get_db
from api.services.model_service import MODEL_VERSION, model_service

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    db_reachable = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_reachable = False

    model_loaded = model_service.is_loaded
    return HealthOut(
        status="ok" if (model_loaded and db_reachable) else "degraded",
        model_loaded=model_loaded,
        db_reachable=db_reachable,
        model_version=MODEL_VERSION,
        # See HealthOut's own docstring comment: lets "why is the
        # dashboard empty" be answered by checking THIS instead of
        # guessing whether some other, stale process is the one actually
        # answering on this port.
        project_root=str(PROJECT_ROOT),
        db_path=str(DB_PATH),
    )
