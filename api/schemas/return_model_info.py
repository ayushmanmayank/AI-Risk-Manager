"""Response schema for GET /api/v1/models/return -- return-model
equivalent of api/schemas/model_info.py.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReturnModelInfoOut(BaseModel):
    model_name: str
    model_version: str
    training_date: datetime
    dataset_version: str
    # Surfaced directly in the response, not just in code comments -- see
    # return_model_info_service.py's DATASET_HONESTY_NOTE docstring.
    dataset_honesty_note: str
    threshold: float

    # Held-out TEST-set metrics, same discipline as ModelInfoOut: never
    # validation, nothing recomputed or re-tuned against it.
    precision: float
    recall: float
    f1: float
    pr_auc: float
    roc_auc: float
    false_positive_rate: float
    false_negative_rate: float

    tp: int
    fp: int
    fn: int
    tn: int
    test_set_size: int
