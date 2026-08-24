"""Tests for Tier 4's analytics response cache: the pure TTLCache
primitive (api/services/ttl_cache.py) and the actual GET /api/v1/analytics
endpoint's measured before/after latency through it.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import api.routes.analytics as analytics_module
from api.main import app

RAW_FEATURE_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]


def _valid_payload(**overrides) -> dict:
    payload = {col: 0.0 for col in RAW_FEATURE_COLUMNS}
    payload["Time"] = 1000.0
    payload["Amount"] = 50.0
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------
# Pure logic.
# ---------------------------------------------------------------------

from api.services.ttl_cache import TTLCache  # noqa: E402


def test_second_call_within_ttl_is_a_cache_hit_not_a_recompute():
    cache: TTLCache[int] = TTLCache(ttl_seconds=10.0)
    calls = []

    def compute():
        calls.append(1)
        return 42

    assert cache.get(compute, now=0.0) == 42
    assert cache.get(compute, now=1.0) == 42  # still within TTL
    assert len(calls) == 1  # compute() only ran once
    assert cache.stats.hits == 1
    assert cache.stats.misses == 1


def test_call_after_ttl_expires_recomputes():
    cache: TTLCache[int] = TTLCache(ttl_seconds=5.0)
    values = iter([1, 2])

    def compute():
        return next(values)

    assert cache.get(compute, now=0.0) == 1
    assert cache.get(compute, now=5.1) == 2  # past the 5s TTL
    assert cache.stats.misses == 2


def test_invalidate_forces_a_recompute():
    cache: TTLCache[int] = TTLCache(ttl_seconds=60.0)
    values = iter([1, 2])
    compute = lambda: next(values)  # noqa: E731

    assert cache.get(compute, now=0.0) == 1
    cache.invalidate()
    assert cache.get(compute, now=0.1) == 2


def test_cache_measurably_avoids_redundant_expensive_recomputation():
    """The actual before/after: an artificially slow compute() (50ms,
    standing in for 'expensive aggregate query'), called 10 times inside
    the TTL. Uncached, 10 calls would cost >=500ms; cached, only the
    first is slow. This is deterministic (no flaky real-DB-speed
    assumption) and measures exactly what caching is supposed to buy.
    """
    cache: TTLCache[int] = TTLCache(ttl_seconds=60.0)
    call_count = 0

    def slow_compute():
        nonlocal call_count
        call_count += 1
        time.sleep(0.05)
        return call_count

    start = time.perf_counter()
    first = cache.get(slow_compute)  # miss: pays the 50ms
    first_call_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(9):
        cache.get(slow_compute)  # 9 hits: should be near-instant
    nine_cached_calls_elapsed = time.perf_counter() - start

    assert call_count == 1  # the expensive function ran exactly once
    assert first == 1
    # The 9 cached calls combined must be dramatically cheaper than even
    # ONE more real computation would have been (50ms) -- generous
    # margin (10ms) to absorb CI/sandbox scheduling noise, not a
    # hair-trigger timing assertion.
    assert nine_cached_calls_elapsed < 0.01
    print(
        f"\n[analytics cache benchmark] first call (miss): {first_call_elapsed*1000:.2f}ms | "
        f"9 subsequent calls (hits) combined: {nine_cached_calls_elapsed*1000:.2f}ms"
    )


# ---------------------------------------------------------------------
# Through the real endpoint.
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


def test_analytics_endpoint_second_call_is_faster_than_first(client, monkeypatch):
    """End-to-end version of the benchmark above: artificially slow down
    the REAL route's compute function, then measure real HTTP round
    trips through TestClient. Proves the caching is actually wired into
    the endpoint, not just correct in isolation.
    """
    real_compute = analytics_module._compute_analytics

    def slow_compute(db):
        time.sleep(0.05)
        return real_compute(db)

    monkeypatch.setattr(analytics_module, "_compute_analytics", slow_compute)

    client.post("/api/v1/predict", json=_valid_payload())

    start = time.perf_counter()
    first_response = client.get("/api/v1/analytics")
    first_elapsed = time.perf_counter() - start
    assert first_response.status_code == 200

    start = time.perf_counter()
    second_response = client.get("/api/v1/analytics")
    second_elapsed = time.perf_counter() - start
    assert second_response.status_code == 200

    # Same data either way -- caching must never change the answer.
    assert first_response.json() == second_response.json()
    # The cached call must be substantially faster -- not a razor-thin
    # margin, since the artificial delay (50ms) dwarfs normal HTTP/test
    # overhead by design.
    assert second_elapsed < first_elapsed / 2
    print(
        f"\n[GET /analytics benchmark] first call (miss, +50ms artificial delay): "
        f"{first_elapsed*1000:.2f}ms | second call (cache hit): {second_elapsed*1000:.2f}ms"
    )
