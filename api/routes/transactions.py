"""GET /api/v1/transactions and GET /api/v1/transactions/{transaction_id}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas.prediction import PaginatedTransactions, PredictionOut
from api.services.db import get_db
from api.services.db_models import PredictionRecord

router = APIRouter()


@router.get("/transactions", response_model=PaginatedTransactions)
def list_transactions(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedTransactions:
    total = db.scalar(select(func.count()).select_from(PredictionRecord)) or 0
    rows = (
        db.execute(
            select(PredictionRecord)
            .order_by(PredictionRecord.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return PaginatedTransactions(
        items=[PredictionOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/transactions/{transaction_id}", response_model=PredictionOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)) -> PredictionOut:
    record = db.get(PredictionRecord, transaction_id)
    if record is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"transaction_id '{transaction_id}' not found"
        )
    return PredictionOut.model_validate(record)
