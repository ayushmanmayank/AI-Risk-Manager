"""Tests for POST /api/v1/simulate (Day 9 Threshold Simulator backend).

Cross-checks against Day 2's src/risk/cost_engine.sweep_thresholds()
directly -- not just asserted in isolation -- by independently
recomputing the validation set's confusion counts the same way
api/services/simulation_service.py does, so a real pipeline drift would
actually be caught here.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.risk.cost_engine import (
    DEFAULT_FALSE_NEGATIVE_COST,
    DEFAULT_FALSE_POSITIVE_COST,
    confusion_counts_at_threshold,
    expected_cost,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def validation_arrays():
    """Independently loads the same validation-set y_true/y_prob that
    api/services/simulation_service.py computes at startup, so the
    cross-check test isn't just comparing the endpoint to itself.
    """
    bundle = joblib.load(PROJECT_ROOT / "models" / "fraud_model_v1.pkl")
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    split = bundle["split_indices"]

    data = (
        pd.read_csv(PROJECT_ROOT / "data" / "processed" / "features.csv", usecols=[*feature_columns, "Class"])
        .sort_values("Time", kind="stable")
        .reset_index(drop=True)
    )
    validation = data.iloc[split["train_end"] : split["validation_end"]]
    y_true = validation["Class"].to_numpy()
    y_prob = model.predict_proba(validation[feature_columns])[:, 1]
    return y_true, y_prob


def test_threshold_zero_flags_everything(client):
    response = client.post("/api/v1/simulate", json={"threshold": 0.0})
    assert response.status_code == 200
    body = response.json()
    # threshold 0.0 -> every row's probability >= 0.0 -> everything flagged.
    assert body["recall"] == pytest.approx(1.0)
    assert body["transactions_affected_count"] == body["validation_set_size"]
    assert body["fn"] == 0
    assert body["tn"] == 0
    # Precision is very low: true fraud rate in validation is ~0.13%.
    assert body["precision"] < 0.01


def test_threshold_one_flags_almost_nothing(client):
    response = client.post("/api/v1/simulate", json={"threshold": 1.0})
    assert response.status_code == 200
    body = response.json()
    # threshold 1.0 -> only probability == 1.0 exactly gets flagged, which
    # is essentially never for a calibrated model -- recall should be very
    # low (near 0), not necessarily exactly 0.
    assert body["recall"] < 0.05
    assert body["transactions_affected_count"] < body["validation_set_size"] * 0.01


@pytest.mark.parametrize("threshold", [0.40, 0.50])
def test_midrange_threshold_matches_day2_sweep(client, validation_arrays, threshold):
    y_true, y_prob = validation_arrays

    expected_tp, expected_fp, expected_fn, expected_tn = confusion_counts_at_threshold(
        y_true, y_prob, threshold
    )
    expected_loss = expected_cost(expected_fp, expected_fn, DEFAULT_FALSE_POSITIVE_COST, DEFAULT_FALSE_NEGATIVE_COST)

    response = client.post("/api/v1/simulate", json={"threshold": threshold})
    assert response.status_code == 200
    body = response.json()

    assert body["tp"] == expected_tp
    assert body["fp"] == expected_fp
    assert body["fn"] == expected_fn
    assert body["tn"] == expected_tn
    assert body["expected_financial_loss"] == pytest.approx(expected_loss)
    assert body["false_positive_cost"] == pytest.approx(DEFAULT_FALSE_POSITIVE_COST)
    assert body["false_negative_cost"] == pytest.approx(DEFAULT_FALSE_NEGATIVE_COST)

    expected_precision = expected_tp / (expected_tp + expected_fp) if (expected_tp + expected_fp) > 0 else 0.0
    expected_recall = expected_tp / (expected_tp + expected_fn) if (expected_tp + expected_fn) > 0 else 0.0
    assert body["precision"] == pytest.approx(expected_precision)
    assert body["recall"] == pytest.approx(expected_recall)


def test_custom_costs_are_respected(client):
    response = client.post(
        "/api/v1/simulate",
        json={"threshold": 0.5, "false_positive_cost": 1.0, "false_negative_cost": 1000.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["false_positive_cost"] == 1.0
    assert body["false_negative_cost"] == 1000.0
    assert body["expected_financial_loss"] == pytest.approx(body["fp"] * 1.0 + body["fn"] * 1000.0)


def test_invalid_threshold_returns_422(client):
    response = client.post("/api/v1/simulate", json={"threshold": 1.5})
    assert response.status_code == 422
