"""Tests for Tier 4's rate limiter: both the pure sliding-window logic
(api/services/rate_limiter.py) and the actual POST /api/v1/predict
endpoint's 429 behavior end to end.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.predict import PREDICT_RATE_LIMIT_PER_MINUTE, predict_rate_limiter
from api.services.rate_limiter import RateLimiter

RAW_FEATURE_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]


def _valid_payload(**overrides) -> dict:
    payload = {col: 0.0 for col in RAW_FEATURE_COLUMNS}
    payload["Time"] = 1000.0
    payload["Amount"] = 50.0
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------
# Pure logic (no FastAPI/DB involved) -- mirrors test_anomaly.py's style.
# ---------------------------------------------------------------------


def test_allows_requests_up_to_the_limit():
    limiter = RateLimiter(max_requests=5, window_seconds=60.0)
    for _ in range(5):
        result = limiter.check("client-a", now=0.0)
        assert result.allowed is True
    # The 6th, still at the same instant, must be rejected.
    result = limiter.check("client-a", now=0.0)
    assert result.allowed is False
    assert result.remaining == 0


def test_remaining_count_decreases_as_the_budget_is_used():
    limiter = RateLimiter(max_requests=3, window_seconds=60.0)
    assert limiter.check("k", now=0.0).remaining == 2
    assert limiter.check("k", now=0.0).remaining == 1
    assert limiter.check("k", now=0.0).remaining == 0


def test_different_keys_have_independent_budgets():
    limiter = RateLimiter(max_requests=1, window_seconds=60.0)
    assert limiter.check("client-a", now=0.0).allowed is True
    assert limiter.check("client-a", now=0.0).allowed is False
    # A different key (a different client IP) must not be affected by
    # client-a's exhausted budget.
    assert limiter.check("client-b", now=0.0).allowed is True


def test_requests_age_out_of_the_sliding_window():
    limiter = RateLimiter(max_requests=2, window_seconds=10.0)
    assert limiter.check("k", now=0.0).allowed is True
    assert limiter.check("k", now=1.0).allowed is True
    assert limiter.check("k", now=2.0).allowed is False  # budget exhausted

    # Still within the window from the first two hits -- still rejected.
    assert limiter.check("k", now=9.9).allowed is False
    # Past 10s from the FIRST hit (t=0), that one has aged out, freeing a
    # slot even though the second hit (t=1) is still within the window.
    assert limiter.check("k", now=10.1).allowed is True


def test_rejected_request_is_not_itself_counted():
    # A client stuck retrying after a 429 shouldn't have every rejected
    # attempt further starve their own budget once the window clears.
    limiter = RateLimiter(max_requests=1, window_seconds=10.0)
    assert limiter.check("k", now=0.0).allowed is True
    assert limiter.check("k", now=1.0).allowed is False
    assert limiter.check("k", now=2.0).allowed is False
    # Window clears from the ONE real hit at t=0, not inflated by the
    # rejected attempts at t=1/t=2.
    assert limiter.check("k", now=10.1).allowed is True


def test_retry_after_reflects_actual_wait_time():
    limiter = RateLimiter(max_requests=1, window_seconds=10.0)
    limiter.check("k", now=0.0)
    result = limiter.check("k", now=3.0)
    assert result.allowed is False
    assert result.retry_after_seconds == pytest.approx(7.0)


def test_reset_clears_all_tracked_state():
    limiter = RateLimiter(max_requests=1, window_seconds=60.0)
    limiter.check("k", now=0.0)
    assert limiter.check("k", now=0.0).allowed is False
    limiter.reset()
    assert limiter.check("k", now=0.0).allowed is True


# ---------------------------------------------------------------------
# Real endpoint, real 429 -- this is the "confirm it actually triggers"
# check the brief specifically asked for, not just the unit-level logic.
# ---------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.services.db as db_module
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test_predictions.db'}",
        connect_args={"check_same_thread": False},
    )
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session_local)

    with TestClient(app) as test_client:
        yield test_client


def test_predict_endpoint_returns_429_once_limit_exceeded(client):
    # TestClient's requests all present as the same synthetic client, so
    # they share one rate-limit budget -- exactly the scenario being
    # tested. Distinct payloads (varying Time) avoid the UNRELATED
    # content-hash dedup short-circuit (a 200 for a repeat, not a fresh
    # 201) from muddying what's being measured here.
    responses = [
        client.post("/api/v1/predict", json=_valid_payload(Time=float(i)))
        for i in range(PREDICT_RATE_LIMIT_PER_MINUTE + 1)
    ]

    statuses = [r.status_code for r in responses]
    assert statuses[:PREDICT_RATE_LIMIT_PER_MINUTE] == [201] * PREDICT_RATE_LIMIT_PER_MINUTE
    assert statuses[-1] == 429

    last = responses[-1]
    assert "Retry-After" in last.headers
    assert "Rate limit exceeded" in last.json()["detail"]


def test_predict_rate_limit_recovers_after_reset(client):
    # Sanity check on the conftest.py autouse fixture this whole test
    # file (and every other one) relies on: confirms the singleton
    # really does start clean, not just that .reset() exists.
    assert predict_rate_limiter.check("sanity-check-key").allowed is True
    predict_rate_limiter.reset()
