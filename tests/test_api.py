"""Tests for the Day 3 FastAPI fraud-scoring API.

Uses a temporary SQLite file per test (by monkeypatching api.services.db's
engine/SessionLocal) so tests never touch data/predictions.db, while still
exercising the real trained model and real feature pipeline end to end.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.services.db as db_module
from api.main import app
from api.services.model_service import model_service

RAW_FEATURE_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]


def _valid_payload(**overrides) -> dict:
    payload = {col: 0.0 for col in RAW_FEATURE_COLUMNS}
    payload["Time"] = 1000.0
    payload["Amount"] = 50.0
    payload.update(overrides)
    return payload


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient wired to an isolated, per-test SQLite database."""
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test_predictions.db'}",
        connect_args={"check_same_thread": False},
    )
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session_local)

    with TestClient(app) as test_client:
        yield test_client


def test_valid_prediction_returns_full_response(client):
    response = client.post("/api/v1/predict", json=_valid_payload())
    assert response.status_code == 201
    body = response.json()
    for field in (
        "transaction_id",
        "fraud_probability",
        "risk_tier",
        "decision",
        "expected_loss",
        "model_version",
        "timestamp",
    ):
        assert field in body
    assert 0.0 <= body["fraud_probability"] <= 1.0
    assert body["risk_tier"] in {"LOW", "MEDIUM", "HIGH"}
    assert body["decision"] in {"ALLOW", "REVIEW", "HOLD"}


def test_prediction_includes_valid_shap_explanation(client):
    response = client.post("/api/v1/predict", json=_valid_payload())
    assert response.status_code == 201
    body = response.json()

    assert "shap_explanation" in body
    explanation = body["shap_explanation"]
    assert "top_positive_features" in explanation
    assert "top_negative_features" in explanation

    positive = explanation["top_positive_features"]
    negative = explanation["top_negative_features"]
    assert 0 <= len(positive) <= 5
    assert 0 <= len(negative) <= 5

    real_columns = set(model_service.feature_columns)
    for contribution in positive + negative:
        for key in ("feature", "label", "shap_value", "feature_value"):
            assert key in contribution
        # Every listed feature must be a real column the model was trained
        # on -- not a hallucinated name.
        assert contribution["feature"] in real_columns
        assert isinstance(contribution["shap_value"], float)
        assert isinstance(contribution["feature_value"], float)

    # Direction sanity: positive contributions push toward fraud (shap > 0),
    # negative contributions push toward legitimate (shap < 0).
    assert all(c["shap_value"] > 0 for c in positive)
    assert all(c["shap_value"] < 0 for c in negative)


def test_get_transaction_includes_shap_explanation(client):
    created = client.post("/api/v1/predict", json=_valid_payload()).json()
    fetched = client.get(f"/api/v1/transactions/{created['transaction_id']}").json()
    assert fetched["shap_explanation"] == created["shap_explanation"]


def test_missing_field_returns_422(client):
    payload = _valid_payload()
    del payload["V14"]
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422


def test_negative_amount_returns_422(client):
    response = client.post("/api/v1/predict", json=_valid_payload(Amount=-10.0))
    assert response.status_code == 422


def test_duplicate_transaction_id_returns_409(client):
    payload = _valid_payload(transaction_id="txn_test_dup_1")
    first = client.post("/api/v1/predict", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/predict", json=payload)
    assert second.status_code == 409


def test_duplicate_content_without_id_returns_existing_prediction(client):
    payload = _valid_payload(Amount=77.77)  # no transaction_id -- content-hash fallback path
    assert "transaction_id" not in payload

    first = client.post("/api/v1/predict", json=payload)
    assert first.status_code == 201
    first_body = first.json()

    second = client.post("/api/v1/predict", json=payload)
    assert second.status_code == 200  # existing prediction returned, not re-scored
    second_body = second.json()

    assert second_body["transaction_id"] == first_body["transaction_id"]
    assert second_body == first_body

    # Only one row actually stored for this content, not two.
    with db_module.SessionLocal() as session:
        from api.services.db_models import PredictionRecord

        count = session.query(PredictionRecord).filter_by(
            transaction_id=first_body["transaction_id"]
        ).count()
        assert count == 1


def test_duplicate_content_with_different_explicit_ids_creates_two_rows(client):
    # An explicit transaction_id always creates its own row, even if the
    # content is identical to a previous submission -- content-hash dedup
    # only applies when no id was supplied (see api/services/dedup.py).
    payload = _valid_payload(Amount=88.88)
    first = client.post("/api/v1/predict", json={**payload, "transaction_id": "explicit-a"})
    second = client.post("/api/v1/predict", json={**payload, "transaction_id": "explicit-b"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["transaction_id"] != second.json()["transaction_id"]


def test_predict_then_get_round_trip(client):
    created = client.post("/api/v1/predict", json=_valid_payload()).json()
    transaction_id = created["transaction_id"]

    fetched = client.get(f"/api/v1/transactions/{transaction_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["transaction_id"] == transaction_id
    assert body["fraud_probability"] == pytest.approx(created["fraud_probability"])
    assert body["decision"] == created["decision"]


def test_get_unknown_transaction_returns_404(client):
    response = client.get("/api/v1/transactions/does-not-exist")
    assert response.status_code == 404


def test_health_reports_model_and_db(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["model_loaded"] is True
    assert body["db_reachable"] is True


def test_analytics_reflects_scored_transactions(client):
    client.post("/api/v1/predict", json=_valid_payload())
    client.post("/api/v1/predict", json=_valid_payload(Amount=200.0))

    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_transactions"] == 2
    assert sum(body["count_by_risk_tier"].values()) == 2
    assert sum(body["count_by_decision"].values()) == 2
