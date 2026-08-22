"""Tests for scripts/reset_demo_data.py.

Uses the exact same isolated-DB pattern as tests/test_api.py (a per-test
temp SQLite file, with api.services.db's engine/SessionLocal monkeypatched
at the module-attribute level) so this never touches data/predictions.db,
while still exercising the real trained model, real feature pipeline, and
real HTTP routes end to end via TestClient.

TestClient (starlette.testclient) subclasses httpx.Client directly, so it
can be handed anywhere reset_demo_data.py expects an httpx.Client -- this
runs the full reset in-process against the real FastAPI app, no separate
running server required.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.services.db as db_module
from api.main import app
from api.services.db_models import AlertRecord, ChargebackRecord, PredictionRecord, RefundRecord
from scripts.reset_demo_data import clear_demo_tables, reset_demo_data
from src.anomaly.spike_detector import DEFAULT_WINDOW_SIZE

API_URL = "/api/v1"  # relative -- resolves against TestClient's base_url


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


def _counts() -> dict[str, int]:
    with db_module.SessionLocal() as session:
        return {
            "predictions": session.query(PredictionRecord).count(),
            "alerts": session.query(AlertRecord).count(),
            "chargebacks": session.query(ChargebackRecord).count(),
            "refunds": session.query(RefundRecord).count(),
        }


def _valid_payload(**overrides) -> dict:
    raw_feature_columns = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    payload = {col: 0.0 for col in raw_feature_columns}
    payload["Time"] = 1000.0
    payload["Amount"] = 50.0
    payload.update(overrides)
    return payload


def test_clear_demo_tables_empties_all_four_tables_on_populated_db(client):
    # Populate something in every table clear_demo_tables is responsible for.
    client.post(f"{API_URL}/predict", json=_valid_payload())
    now = datetime(2024, 1, 1)
    with db_module.SessionLocal() as session:
        session.add(
            ChargebackRecord(
                chargeback_id="cb_test",
                transaction_id="does-not-need-to-exist-for-this-check",
                reason="fraudulent_card_use",
                amount=1.0,
                timestamp=now,
                status="pending",
            )
        )
        session.add(
            RefundRecord(
                refund_id="rf_test",
                transaction_id="does-not-need-to-exist-for-this-check",
                amount=1.0,
                timestamp=now,
                reason="customer_dispute_pre_chargeback",
            )
        )
        session.add(
            AlertRecord(
                alert_id="alert_test",
                alert_type="fraud_spike",
                severity="high",
                description="test alert",
            )
        )
        session.commit()

    before = _counts()
    assert all(v > 0 for v in before.values()), f"fixture setup failed to populate all tables: {before}"

    cleared = clear_demo_tables()

    after = _counts()
    assert all(v == 0 for v in after.values()), f"tables not fully cleared: {after}"
    for table, count in cleared.items():
        assert count == before[table]


def test_clear_demo_tables_is_a_noop_on_already_empty_db(client):
    assert all(v == 0 for v in _counts().values())
    cleared = clear_demo_tables()
    assert all(v == 0 for v in cleared.values())
    assert all(v == 0 for v in _counts().values())


def test_reset_demo_data_from_fresh_db_produces_seeded_calm_state(client):
    summary = reset_demo_data(client, api_url=API_URL, seed=42)

    assert summary["baseline_high_failed"] == 0
    assert summary["baseline_normal_failed"] == 0
    assert summary["cooldown_failed"] == 0

    counts = _counts()
    assert counts["predictions"] > 0
    assert counts["chargebacks"] > 0  # seed_chargebacks.py's 3 HIGH + 3-4 LOW picks

    # The whole point of the cooldown batch: the detector reads calm
    # immediately after a reset, not "active" from the baseline HIGH rows.
    assert summary["is_spike_active_after_reset"] is False
    assert summary["window_size_after_reset"] == DEFAULT_WINDOW_SIZE


def test_reset_demo_data_recovers_from_exhausted_high_pool(client):
    """Recreates the Day 12 audit's failure scenario: hammer every HIGH row
    in the test split via repeated content-hash-deduped sends, THEN reset,
    and confirm the reset still lands in an identical calm/seeded state --
    proving the reset doesn't depend on any HIGH rows being "unclaimed"
    going in.
    """
    from simulator.simulate import load_test_split, rank_by_fraud_probability

    test_data = load_test_split()
    ranked = rank_by_fraud_probability(test_data)
    high_rows = ranked[ranked["_fraud_probability"] >= 0.70]
    assert len(high_rows) > 0

    from scripts.reset_demo_data import _send_batch

    _send_batch(client, API_URL, high_rows)  # claim the entire HIGH pool
    exhausted_counts = _counts()
    assert exhausted_counts["predictions"] == len(high_rows)

    summary = reset_demo_data(client, api_url=API_URL, seed=42)

    assert summary["is_spike_active_after_reset"] is False
    counts = _counts()
    assert counts["chargebacks"] > 0


def test_reset_demo_data_from_mid_demo_state_reaches_same_calm_state(client):
    """Simulates: some normal traffic already sent, then a live spike
    burst triggered (detector now reads active), before the reset runs.
    """
    from simulator.simulate import load_test_split, rank_by_fraud_probability

    for i in range(5):
        client.post(f"{API_URL}/predict", json=_valid_payload(Amount=10.0 + i))

    test_data = load_test_split()
    ranked = rank_by_fraud_probability(test_data)
    high_rows = ranked.sort_values("_fraud_probability", ascending=False).head(10)
    from scripts.reset_demo_data import _send_batch

    _send_batch(client, API_URL, high_rows)

    mid_demo_alerts = client.get(f"{API_URL}/alerts").json()
    assert mid_demo_alerts["is_spike_active"] is True  # confirms the "mid-demo, spike active" premise

    summary = reset_demo_data(client, api_url=API_URL, seed=7)

    assert summary["is_spike_active_after_reset"] is False


def test_reset_demo_data_is_idempotent_when_run_twice_in_a_row(client):
    first = reset_demo_data(client, api_url=API_URL, seed=1)
    first_counts = _counts()

    second = reset_demo_data(client, api_url=API_URL, seed=2)
    second_counts = _counts()

    assert first["is_spike_active_after_reset"] is False
    assert second["is_spike_active_after_reset"] is False
    # Same shape of end state both times (predictions count is
    # deterministic: baseline + cooldown sends, minus zero clashes since
    # the table was cleared first each time).
    assert first_counts.keys() == second_counts.keys()
    assert second_counts["predictions"] == first_counts["predictions"]
    assert second_counts["chargebacks"] == first_counts["chargebacks"]
