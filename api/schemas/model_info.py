"""Response schema for GET /api/v1/models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ModelInfoOut(BaseModel):
    model_name: str
    model_version: str
    training_date: datetime
    dataset_version: str
    threshold: float

    # Held-out TEST-set metrics (see api/services/model_info_service.py) --
    # NOT validation. This is the one deliberate, already-audited (Day 5)
    # look at test; nothing recomputes or re-tunes against it.
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
