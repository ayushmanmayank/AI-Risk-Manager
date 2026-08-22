"""Response schemas for the prediction, transactions, analytics, and health
endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShapFeatureContribution(BaseModel):
    feature: str
    label: str
    shap_value: float
    feature_value: float


class ShapExplanationOut(BaseModel):
    top_positive_features: list[ShapFeatureContribution]
    top_negative_features: list[ShapFeatureContribution]


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    amount: float
    fraud_probability: float
    risk_tier: str
    decision: str
    expected_loss: float
    model_version: str
    timestamp: datetime
    shap_explanation: ShapExplanationOut


class PaginatedTransactions(BaseModel):
    items: list[PredictionOut]
    total: int
    limit: int
    offset: int


class AnalyticsOut(BaseModel):
    total_transactions: int
    count_by_risk_tier: dict[str, int]
    count_by_decision: dict[str, int]
    average_expected_loss: float
    high_tier_fraud_rate: float | None
    high_tier_fraud_rate_note: str


class HealthOut(BaseModel):
    status: str
    model_loaded: bool
    db_reachable: bool
    model_version: str
