"""Wires the pure spike-detection logic (src/anomaly/spike_detector.py) to
live prediction data and persists alert events so spike history survives
beyond the live rolling window.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.services.db_models import AlertRecord, PredictionRecord
from src.anomaly.spike_detector import (
    DEFAULT_WINDOW_SIZE,
    SpikeDetectionResult,
    detect_spike,
)
from src.risk.decision_engine import DEFAULT_HIGH_THRESHOLD

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"

ALERT_TYPE_FRAUD_SPIKE = "fraud_rate_spike"


class AnomalyService:
    """Holds the training-derived baseline HIGH-tier rate, loaded once at
    API startup, and evaluates the live rolling window against it on demand.
    """

    def __init__(self) -> None:
        self.baseline_fraud_rate: float = 0.0
        self._loaded = False

    def load(self) -> None:
        """Compute the baseline by scoring the TRAINING split (never
        validation/test) with the trained model, at the same high_threshold
        the decision engine uses everywhere else -- see
        src/anomaly/spike_detector.py's module docstring for why this must
        be a model-predicted rate, not the raw ground-truth Class rate.
        """
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]
        train_end = bundle["split_indices"]["train_end"]

        data = (
            pd.read_csv(FEATURES_PATH, usecols=feature_columns)  # feature_columns already includes Time
            .sort_values("Time", kind="stable")
            .reset_index(drop=True)
        )
        train = data.iloc[:train_end]
        probabilities = model.predict_proba(train[feature_columns])[:, 1]
        self.baseline_fraud_rate = float((probabilities >= DEFAULT_HIGH_THRESHOLD).mean())
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def current_status(
        self, db: Session, window_size: int = DEFAULT_WINDOW_SIZE
    ) -> tuple[SpikeDetectionResult, datetime | None]:
        """Returns the detection result plus the timestamp of the OLDEST
        prediction in the window -- used to tell whether an active spike is
        a continuation of an already-logged episode or a brand-new one.
        """
        rows = db.execute(
            select(PredictionRecord.risk_tier, PredictionRecord.timestamp)
            .order_by(PredictionRecord.timestamp.desc())
            .limit(window_size)
        ).all()
        tiers = [row.risk_tier for row in rows]
        oldest_timestamp = rows[-1].timestamp if rows else None
        result = detect_spike(tiers, baseline_fraud_rate=self.baseline_fraud_rate)
        return result, oldest_timestamp

    def ensure_alert_logged(
        self,
        db: Session,
        result: SpikeDetectionResult,
        window_oldest_timestamp: datetime | None,
    ) -> datetime:
        """Log a new alert event only if this spike is a NEW episode, not a
        continuation of one already logged during the current window's
        span. Returns the episode's first-detected timestamp either way.
        Caller must already have confirmed result.is_spike is True.
        """
        latest = db.execute(
            select(AlertRecord)
            .where(AlertRecord.alert_type == ALERT_TYPE_FRAUD_SPIKE)
            .order_by(AlertRecord.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest is not None and window_oldest_timestamp is not None and latest.created_at >= window_oldest_timestamp:
            return latest.created_at  # still the same ongoing episode

        alert = AlertRecord(
            alert_id=f"alert_{uuid.uuid4().hex}",
            alert_type=ALERT_TYPE_FRAUD_SPIKE,
            severity=result.severity,
            description=(
                f"Fraud rate spike detected: {result.current_fraud_rate:.2%} of the last "
                f"{result.window_size} predictions were HIGH risk (baseline "
                f"{result.baseline_fraud_rate:.3%}), anomaly_score={result.anomaly_score:.2f}"
            ),
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert.created_at


# Process-wide singleton, loaded once from api/main.py's startup hook.
anomaly_service = AnomalyService()
