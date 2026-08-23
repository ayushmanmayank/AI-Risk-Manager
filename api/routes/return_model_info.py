"""GET /api/v1/models/return -- return-risk model metadata + real held-out
TEST-set metrics. Separate route/response from GET /api/v1/models
(the fraud model) so the two models' metrics are never blended into one
payload -- see api/services/return_model_info_service.py for why.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.schemas.return_model_info import ReturnModelInfoOut
from api.services.return_model_info_service import return_model_info_service

router = APIRouter()


@router.get("/models/return", response_model=ReturnModelInfoOut)
def get_return_model_info() -> ReturnModelInfoOut:
    if not return_model_info_service.is_loaded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Return model info not loaded")
    return ReturnModelInfoOut(**return_model_info_service.info)
