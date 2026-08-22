"""GET /api/v1/models -- model metadata + real held-out TEST-set metrics.

See api/services/model_info_service.py for why TEST (not validation).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.schemas.model_info import ModelInfoOut
from api.services.model_info_service import model_info_service

router = APIRouter()


@router.get("/models", response_model=ModelInfoOut)
def get_model_info() -> ModelInfoOut:
    if not model_info_service.is_loaded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model info not loaded")
    return ModelInfoOut(**model_info_service.info)
