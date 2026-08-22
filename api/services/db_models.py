"""SQLAlchemy ORM model for the predictions table.

SHAP explanations are stored at prediction time (in the same row as the
prediction), not recomputed on GET. Two reasons: (1) it's the only way to
guarantee the explanation shown for a stored prediction always matches the
model_version that made it -- recomputing on-demand against whatever model
is currently loaded would silently mismatch old rows the moment the model
is retrained/replaced; (2) TreeExplainer.shap_values() is not free, and
GET /transactions/{id} should stay a cheap read.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from api.services.db import Base


class PredictionRecord(Base):
    __tablename__ = "predictions"

    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    time: Mapped[float] = mapped_column(Float, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    fraud_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False, index=True)
    expected_loss: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    # Each stored as a list of dicts shaped like
    # api/schemas/prediction.py:ShapFeatureContribution.
    top_positive_features: Mapped[list] = mapped_column(JSON, nullable=False)
    top_negative_features: Mapped[list] = mapped_column(JSON, nullable=False)
    # sha256 of the raw Time/Amount/V1-V28 payload (see api/services/dedup.py).
    # Nullable at the DB level: rows written before this column existed (via
    # the db.py migration) have no way to be backfilled -- their raw V1-V28
    # values were never persisted anywhere -- so they simply carry NULL and
    # never match a content-hash lookup, which is the correct behavior for
    # predictions that predate the dedup feature.
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    @property
    def shap_explanation(self) -> dict:
        """Nests the two flat columns to match PredictionOut.shap_explanation
        without a schema migration to a single JSON blob column.
        """
        return {
            "top_positive_features": self.top_positive_features,
            "top_negative_features": self.top_negative_features,
        }


class AlertRecord(Base):
    """A persisted anomaly-detection alert event (see
    api/services/anomaly_service.py and src/anomaly/spike_detector.py).

    One row per NEWLY detected episode, not one row per poll -- an
    ongoing spike that's still active the next time GET /alerts is called
    does not get a fresh row; see anomaly_service.ensure_alert_logged for
    the dedup logic.
    """

    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )


class ChargebackRecord(Base):
    """A chargeback event (Day 11). SIMULATED/SEEDED data -- see
    src/evidence/seed_chargebacks.py. No real chargeback history exists;
    this table lets the evidence responder demo have something to show,
    layered onto real transaction/prediction records.
    """

    __tablename__ = "chargebacks"

    chargeback_id: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)


class RefundRecord(Base):
    """A refund event (Day 11). SIMULATED/SEEDED data, same caveat as
    ChargebackRecord above.
    """

    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
