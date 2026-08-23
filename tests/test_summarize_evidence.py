"""Tests for src/evidence/summarize_evidence.py and its integration into
GET /api/v1/chargebacks/{id} (api/routes/chargebacks.py).

This is a pure Python template over an already-assembled EvidencePackage
-- no external API, no LLM, no network call, no API key. So "does not
fabricate" here is fully provable by unit test (unlike an LLM, whose
actual output can't be guaranteed by inspecting the prompt alone): every
clause in generate_summary()'s output is checked below to trace to a
literal field already on the EvidencePackage passed in.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.services.db as db_module
from api.main import app
from api.services.db_models import ChargebackRecord
from src.evidence.evidence_engine import build_evidence_package
from src.evidence.summarize_evidence import generate_summary

RAW_FEATURE_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]


def _valid_payload(**overrides) -> dict:
    payload = {col: 0.0 for col in RAW_FEATURE_COLUMNS}
    payload["Time"] = 1000.0
    payload["Amount"] = 50.0
    payload.update(overrides)
    return payload


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient wired to an isolated, per-test SQLite database -- same
    pattern as tests/test_api.py.
    """
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test_predictions.db'}",
        connect_args={"check_same_thread": False},
    )
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session_local)

    with TestClient(app) as test_client:
        yield test_client


def _sample_chargeback(**overrides) -> dict:
    chargeback = {
        "chargeback_id": "cb_test123",
        "transaction_id": "txn_test123",
        "reason": "fraudulent_card_use",
        "amount": 250.00,
        "timestamp": datetime(2024, 3, 5, tzinfo=timezone.utc),
        "status": "pending",
    }
    chargeback.update(overrides)
    return chargeback


def _sample_transaction(**overrides) -> dict:
    transaction = {
        "transaction_id": "txn_test123",
        "time": 5000.0,
        "amount": 250.00,
        "fraud_probability": 0.87,
        "risk_tier": "HIGH",
        "decision": "HOLD",
        "expected_loss": 217.50,
        "model_version": "fraud_model_v1",
        "timestamp": datetime(2024, 3, 3, tzinfo=timezone.utc),
        "shap_explanation": {
            "top_positive_features": [
                {"feature": "hour_of_day", "label": "Hour of day", "shap_value": 1.2345, "feature_value": 3.0},
                {"feature": "V14", "label": "Anonymized signal V14", "shap_value": 0.9821, "feature_value": -2.1},
            ],
            "top_negative_features": [
                {
                    "feature": "amount_zscore",
                    "label": "Amount vs. recent spending pattern",
                    "shap_value": -0.5,
                    "feature_value": 0.1,
                },
            ],
        },
    }
    transaction.update(overrides)
    return transaction


def _sample_refund(**overrides) -> dict:
    refund = {
        "refund_id": "rf_test123",
        "transaction_id": "txn_test123",
        "amount": 250.00,
        "timestamp": datetime(2024, 3, 4, tzinfo=timezone.utc),
        "reason": "customer_dispute_pre_chargeback",
    }
    refund.update(overrides)
    return refund


# --- generate_summary() -- flagged-in-advance (HOLD) case ---------------


def test_flagged_in_advance_summary_traces_every_clause_to_a_real_field():
    chargeback = _sample_chargeback()
    transaction = _sample_transaction()
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    assert result.available is True
    assert result.error is None
    text = result.text
    # risk_tier
    assert "HIGH risk" in text
    # fraud_probability (0.87 -> 87.0%)
    assert "87.0%" in text
    # timing: chargeback filed 2024-03-05, transaction scored 2024-03-03 -> 2 days
    assert "2 days before the chargeback was filed" in text
    # top_positive_features labels, verbatim (case-adjusted only for
    # mid-sentence grammar -- the feature code itself, "V14", is never
    # touched), never invented meanings
    assert "hour of day" in text.lower()
    assert "anonymized signal V14" in text
    # no refund on file
    assert "No refund was issued prior to the dispute." in text


# --- generate_summary() -- not-flagged (ALLOW) case ----------------------


def test_not_flagged_summary_traces_every_clause_to_a_real_field():
    chargeback = _sample_chargeback(timestamp=datetime(2024, 3, 10, tzinfo=timezone.utc))
    transaction = _sample_transaction(
        risk_tier="LOW",
        decision="ALLOW",
        fraud_probability=0.02,
        timestamp=datetime(2024, 3, 8, tzinfo=timezone.utc),
    )
    refund = _sample_refund(amount=99.99, timestamp=datetime(2024, 3, 9, tzinfo=timezone.utc))
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=refund)

    result = generate_summary(package)

    assert result.available is True
    text = result.text
    assert "LOW risk" in text
    assert "2.0%" in text
    assert "allowed through" in text
    assert "not caught until the chargeback arrived" in text
    # top_negative_features label, verbatim
    assert "amount vs. recent spending pattern" in text.lower()
    # refund clause: amount and date both traceable to the refund dict
    assert "$99.99" in text
    assert "2024-03-09" in text


# --- concrete fabrication guard: missing prediction record --------------


def test_missing_transaction_states_not_available_and_invents_nothing():
    chargeback = _sample_chargeback()
    package = build_evidence_package(chargeback=chargeback, transaction=None, refund=None)

    result = generate_summary(package)

    assert result.available is True
    text = result.text
    assert "No prior risk prediction exists for this transaction_id" in text
    assert "isn't possible to say whether it was flagged in advance" in text
    assert "No refund was issued prior to the dispute." in text
    # None of these ever got a chance to be invented -- confirm they don't appear.
    for forbidden in ("HIGH risk", "LOW risk", "MEDIUM risk", "primarily due to", "largely due to"):
        assert forbidden not in text


def test_missing_refund_states_not_available_and_invents_no_amount():
    chargeback = _sample_chargeback()
    transaction = _sample_transaction()
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    assert "No refund was issued prior to the dispute." in result.text
    assert "refund of $" not in result.text.lower()


def test_summary_never_invents_a_meaning_for_anonymized_shap_features():
    chargeback = _sample_chargeback()
    transaction = _sample_transaction()
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    # The label's feature code is used verbatim ("V14"; only the leading
    # word's case is adjusted for mid-sentence grammar); nothing in the
    # codebase knows what V14 "really" represents, so the summary must
    # never claim to (e.g. never say "device", "location", "IP").
    assert "anonymized signal V14" in result.text
    for invented_meaning in ("device", "location", "ip address", "browser", "geolocation"):
        assert invented_meaning not in result.text.lower()


def test_summary_never_uses_hedging_language_not_present_in_source_data():
    chargeback = _sample_chargeback()
    transaction = _sample_transaction()
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    for hedge_word in ("likely", "probably", "presumably", "seems", "appears to"):
        assert hedge_word not in result.text.lower()


# --- timing edge cases ----------------------------------------------------


def test_timing_same_day_is_described_as_less_than_a_day():
    chargeback = _sample_chargeback(timestamp=datetime(2024, 3, 3, 5, 0, tzinfo=timezone.utc))
    transaction = _sample_transaction(timestamp=datetime(2024, 3, 3, 1, 0, tzinfo=timezone.utc))
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    assert "less than a day before the chargeback was filed" in result.text


def test_timing_scored_after_chargeback_is_stated_plainly_not_hidden():
    # An unusual but real state -- must not be silently forced into "N
    # days before" phrasing, which would misrepresent the actual order.
    chargeback = _sample_chargeback(timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc))
    transaction = _sample_transaction(timestamp=datetime(2024, 3, 5, tzinfo=timezone.utc))
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    assert "after the chargeback was filed" in result.text
    assert "before the chargeback" not in result.text


# --- no external dependency: no key, no network, always available -------


def test_generate_summary_never_touches_environment_or_network(monkeypatch):
    # There must be no ANTHROPIC_API_KEY (or any other env var) lookup
    # left in this module at all -- confirm the summary is generated
    # identically regardless of what's in the environment.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    chargeback = _sample_chargeback()
    transaction = _sample_transaction()
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    result = generate_summary(package)

    assert result.available is True
    assert result.error is None


# --- end-to-end: the chargeback endpoint includes the summary ------------


def test_chargeback_endpoint_includes_auto_summary_and_full_package(client):
    created = client.post("/api/v1/predict", json=_valid_payload(transaction_id="txn_endpoint_test")).json()
    with db_module.SessionLocal() as db:
        db.add(
            ChargebackRecord(
                chargeback_id="cb_endpoint_test",
                transaction_id=created["transaction_id"],
                reason="fraudulent_card_use",
                amount=50.0,
                timestamp=datetime(2024, 1, 1),
                status="pending",
            )
        )
        db.commit()

    response = client.get("/api/v1/chargebacks/cb_endpoint_test")

    assert response.status_code == 200
    body = response.json()
    assert body["auto_summary"]["available"] is True
    assert body["auto_summary"]["text"] is not None
    assert body["auto_summary"]["error"] is None
    # The rest of the evidence package is present and correct alongside it.
    assert body["chargeback"]["chargeback_id"] == "cb_endpoint_test"
    assert body["transaction"]["transaction_id"] == created["transaction_id"]
    assert len(body["timeline"]) > 0
