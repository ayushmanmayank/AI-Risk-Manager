"""Wires the pure PSI drift-detection logic (src/monitoring/drift_detector.py)
to the training feature distribution (baseline, loaded once at startup) and
live scored-prediction data (recent traffic, read fresh on each request).

FEATURE CHOICE AND WHY EACH ONE IS COMPUTED THE WAY IT IS:

- Amount: stored directly on PredictionRecord, both sides. No computation
  needed, no formula to keep consistent.

- fraud_probability: the model's OWN predicted probability on both sides
  (training-split predict_proba for the baseline, the stored
  PredictionRecord.fraud_probability for live) -- never the training
  split's ground-truth Class label. Comparing a model-predicted rate on
  one side against a ground-truth rate on the other would be the same
  apples-to-oranges mistake anomaly_service.py's docstring calls out for
  the spike detector's baseline_fraud_rate.

- hour_of_day: a pure per-row function of Time (see
  src/features/build_features.py:add_hour_of_day) with no rolling
  history -- identical formula on both sides is trivial: read the
  precomputed training column, and derive it from PredictionRecord.time
  live, the same way.

  CONCRETE OBSERVED CAVEAT, not hypothetical: this feature reliably shows
  the largest PSI of the four in an actual demo session -- verified
  directly (68 live predictions clustered entirely in hour_of_day 18-23,
  vs. a roughly uniform 0-23 spread in training). This is NOT a real
  time-of-day traffic-pattern shift. `Time` is "seconds since the first
  transaction in the dataset," not wall-clock time, and simulator/demo
  traffic replays test-split rows, which occupy a narrow contiguous slice
  near the end of that ~48-hour window -- so hour_of_day is structurally
  clustered for ANY small demo session, regardless of whether anything is
  actually wrong. Left in deliberately (the brief asked for it as an
  example feature, and it genuinely demonstrates the detector correctly
  flagging a real distributional difference) but flag this reading to
  anyone looking at it: at this data volume, a hour_of_day flag says much
  more about "how much of the test split has been replayed so far" than
  about any meaningful drift.

- amount_zscore: this one needs care. features.csv's precomputed
  amount_zscore column (used for TRAINING the model) is a *rolling*
  z-score over up to the prior 10,000 transactions
  (add_amount_zscore_batch) -- a completely different formula from what a
  single live transaction actually gets scored with, which is the
  *static reference* z-score (amount_zscore_from_reference, using a fixed
  training mean/std -- see api/services/feature_service.py). Diffing
  those two would show "drift" that is really just a formula mismatch,
  not a real distribution shift. So both sides here use
  amount_zscore_from_reference with the SAME reference mean/std,
  recomputed independently from this module's own training read (not
  borrowed from model_service's singleton, to keep this module
  self-contained and loadable in any order -- same independence
  anomaly_service.py already has from model_service).
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.services.db_models import PredictionRecord
from src.features.build_features import amount_zscore_from_reference
from src.monitoring.drift_detector import (
    DEFAULT_LIVE_SAMPLE_SIZE,
    DriftReport,
    detect_drift,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"

MONITORED_FEATURES = ("Amount", "amount_zscore", "hour_of_day", "fraud_probability")


class DriftService:
    """Holds the training-derived reference (baseline) distributions,
    loaded once at API startup, and evaluates live traffic against them on
    demand -- same lifecycle shape as AnomalyService/ModelService.
    """

    def __init__(self) -> None:
        self.reference_by_feature: dict[str, np.ndarray] = {}
        self.amount_reference_mean: float = 0.0
        self.amount_reference_std: float = 0.0
        self._loaded = False

    def load(self) -> None:
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]
        train_end = bundle["split_indices"]["train_end"]

        needed_columns = sorted(set(feature_columns) | {"Time", "Amount", "hour_of_day"})
        data = (
            pd.read_csv(FEATURES_PATH, usecols=needed_columns)
            .sort_values("Time", kind="stable")
            .reset_index(drop=True)
        )
        train = data.iloc[:train_end]

        self.amount_reference_mean = float(train["Amount"].mean())
        self.amount_reference_std = float(train["Amount"].std())

        probabilities = model.predict_proba(train[feature_columns])[:, 1]

        self.reference_by_feature = {
            "Amount": train["Amount"].to_numpy(dtype=float),
            "amount_zscore": np.array(
                [
                    amount_zscore_from_reference(
                        amount, self.amount_reference_mean, self.amount_reference_std
                    )
                    for amount in train["Amount"]
                ],
                dtype=float,
            ),
            "hour_of_day": train["hour_of_day"].to_numpy(dtype=float),
            "fraud_probability": probabilities.astype(float),
        }
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def current_report(
        self, db: Session, live_sample_size: int = DEFAULT_LIVE_SAMPLE_SIZE
    ) -> DriftReport:
        rows = db.execute(
            select(
                PredictionRecord.time,
                PredictionRecord.amount,
                PredictionRecord.fraud_probability,
            )
            .order_by(PredictionRecord.timestamp.desc())
            .limit(live_sample_size)
        ).all()

        live_by_feature = {
            "Amount": [row.amount for row in rows],
            "amount_zscore": [
                amount_zscore_from_reference(
                    row.amount, self.amount_reference_mean, self.amount_reference_std
                )
                for row in rows
            ],
            "hour_of_day": [(row.time % 86_400) // 3_600 for row in rows],
            "fraud_probability": [row.fraud_probability for row in rows],
        }
        return detect_drift(self.reference_by_feature, live_by_feature)


# Process-wide singleton, loaded once from api/main.py's startup hook.
drift_service = DriftService()
