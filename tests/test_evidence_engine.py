"""Tests for src/evidence/evidence_engine.py's pure assembly logic.

Constructs input dicts directly (no DB) -- matches the pattern already
used for src/anomaly/spike_detector.py's tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.evidence.evidence_engine import CUSTOMER_NOT_AVAILABLE, build_evidence_package

BASE_TIME = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)


def _transaction(risk_tier: str, decision: str, fraud_probability: float) -> dict:
    return {
        "transaction_id": "txn_test123",
        "time": 100000.0,
        "amount": 250.0,
        "fraud_probability": fraud_probability,
        "risk_tier": risk_tier,
        "decision": decision,
        "expected_loss": fraud_probability * 250.0,
        "model_version": "fraud_model_v1",
        "timestamp": BASE_TIME,
        "shap_explanation": {"top_positive_features": [], "top_negative_features": []},
    }


def _chargeback(transaction_id: str = "txn_test123") -> dict:
    return {
        "chargeback_id": "cb_test1",
        "transaction_id": transaction_id,
        "reason": "unauthorized_transaction",
        "amount": 250.0,
        "timestamp": BASE_TIME + timedelta(days=3),
        "status": "lost",
    }


def test_previously_high_risk_transaction_shows_flagged_in_advance():
    transaction = _transaction(risk_tier="HIGH", decision="HOLD", fraud_probability=0.86)
    package = build_evidence_package(chargeback=_chargeback(), transaction=transaction, refund=None)

    assert package.summary.was_flagged_in_advance is True
    assert package.summary.risk_tier_at_scoring == "HIGH"
    assert package.summary.decision_at_scoring == "HOLD"
    assert "already" in package.summary.narrative.lower()
    assert "flagged" in package.summary.narrative.lower() or "suspicious" in package.summary.narrative.lower()


def test_previously_low_risk_transaction_shows_not_flagged_honestly():
    transaction = _transaction(risk_tier="LOW", decision="ALLOW", fraud_probability=0.0003)
    package = build_evidence_package(chargeback=_chargeback(), transaction=transaction, refund=None)

    assert package.summary.was_flagged_in_advance is False
    assert package.summary.risk_tier_at_scoring == "LOW"
    assert package.summary.decision_at_scoring == "ALLOW"
    assert "not" in package.summary.narrative.lower()
    assert "caught" in package.summary.narrative.lower() or "flag" in package.summary.narrative.lower()


def test_missing_prediction_record_does_not_crash_and_says_so():
    package = build_evidence_package(chargeback=_chargeback(), transaction=None, refund=None)

    assert package.transaction is None
    assert package.risk_prediction is None
    assert package.summary.was_flagged_in_advance is False
    assert package.summary.risk_tier_at_scoring is None
    assert "no prior risk prediction" in package.summary.narrative.lower()
    # The timeline itself must say so too, not omit the gap silently.
    assert any(event.event == "transaction_lookup_failed" for event in package.timeline)
    assert any("no prior risk data" in event.description.lower() for event in package.timeline)


def test_customer_is_always_explicitly_not_available():
    package = build_evidence_package(
        chargeback=_chargeback(),
        transaction=_transaction("HIGH", "HOLD", 0.9),
        refund=None,
    )
    assert package.customer == CUSTOMER_NOT_AVAILABLE
    assert "not available" in package.customer.lower()


def test_timeline_is_chronologically_ordered_with_refund():
    transaction = _transaction(risk_tier="LOW", decision="ALLOW", fraud_probability=0.0003)
    refund = {
        "refund_id": "rf_test1",
        "transaction_id": "txn_test123",
        "amount": 250.0,
        "timestamp": BASE_TIME + timedelta(days=1),
        "reason": "customer_dispute_pre_chargeback",
    }
    package = build_evidence_package(chargeback=_chargeback(), transaction=transaction, refund=refund)

    timestamps = [e.timestamp for e in package.timeline if e.timestamp is not None]
    assert timestamps == sorted(timestamps), "timeline events must be in chronological order"

    event_order = [e.event for e in package.timeline]
    # transaction events must precede the refund, which must precede the chargeback.
    assert event_order.index("transaction_scored") < event_order.index("refund_issued")
    assert event_order.index("refund_issued") < event_order.index("chargeback_filed")


def test_all_referenced_ids_are_present_and_consistent():
    transaction = _transaction(risk_tier="HIGH", decision="HOLD", fraud_probability=0.9)
    chargeback = _chargeback()
    package = build_evidence_package(chargeback=chargeback, transaction=transaction, refund=None)

    assert package.chargeback_id == chargeback["chargeback_id"]
    assert package.transaction_id == chargeback["transaction_id"]
    assert package.transaction["transaction_id"] == chargeback["transaction_id"]
    # risk_prediction is documented to be the same record as transaction.
    assert package.risk_prediction is package.transaction
