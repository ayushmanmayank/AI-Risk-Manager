"""Request/response schemas for POST /api/v1/simulate."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.risk.cost_engine import DEFAULT_FALSE_NEGATIVE_COST, DEFAULT_FALSE_POSITIVE_COST


class SimulateRequest(BaseModel):
    threshold: float = Field(..., ge=0.0, le=1.0)
    # Defaults reuse Day 2's cost_engine.py constants verbatim -- these are
    # still placeholder unit-costs (5 and 100), not calibrated real
    # currency figures. See expected_financial_loss's note in
    # SimulateResponse below.
    false_positive_cost: float = Field(default=DEFAULT_FALSE_POSITIVE_COST, ge=0.0)
    false_negative_cost: float = Field(default=DEFAULT_FALSE_NEGATIVE_COST, ge=0.0)


class SimulateResponse(BaseModel):
    threshold: float
    false_positive_cost: float
    false_negative_cost: float

    precision: float
    recall: float
    false_positive_rate: float

    fraud_caught_count: int
    fraud_caught_percent: float
    transactions_affected_count: int
    transactions_affected_percent: float

    # NOTE: this is cost_engine.expected_cost() renamed for the page's
    # audience -- it's still (fp_count * false_positive_cost) + (fn_count *
    # false_negative_cost) in placeholder unit-costs, not a real, calibrated
    # dollar figure. Don't read it as "actual money at stake" without
    # substituting real cost estimates for false_positive_cost/
    # false_negative_cost.
    expected_financial_loss: float

    tp: int
    fp: int
    fn: int
    tn: int
    validation_set_size: int
