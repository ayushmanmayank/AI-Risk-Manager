"""A minimal single-value TTL cache.

WHY HAND-ROLLED, NOT REDIS (the brief allowed a short in-memory TTL):
same reasoning as api/services/rate_limiter.py -- this is a single-process
deployment today, Redis would be a new infrastructure dependency (a whole
extra container in docker-compose.yml) to cache one aggregate query that
takes single-digit milliseconds, and the honest scaling story (this
wouldn't survive multiple replicas correctly) is named explicitly in
README's Production Considerations section rather than solved
prematurely here.

This is deliberately NOT a general-purpose multi-key cache (no LRU, no
per-key TTL) -- GET /api/v1/analytics is the one endpoint this Tier asked
to cache, and a single cached value keyed by nothing is the simplest
correct thing that could possibly work for that. Reach for something
bigger only when a second call site actually needs it.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class TTLCacheStats:
    hits: int
    misses: int


class TTLCache(Generic[T]):
    """Caches the return value of `compute()` for `ttl_seconds`. Thread-
    safe for uvicorn's single-process-multi-thread-pool model (FastAPI
    runs sync route handlers in a thread pool even with one worker
    process) -- a lock around the read-recompute-write path avoids two
    concurrent misses both recomputing redundantly, which would defeat
    half the point of caching under real concurrent load.
    """

    def __init__(self, ttl_seconds: float) -> None:
        self.ttl_seconds = ttl_seconds
        self._value: T | None = None
        self._cached_at: float | None = None
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, compute: Callable[[], T], now: float | None = None) -> T:
        current_time = time.monotonic() if now is None else now
        with self._lock:
            is_fresh = (
                self._cached_at is not None
                and (current_time - self._cached_at) < self.ttl_seconds
            )
            if is_fresh:
                self._hits += 1
                return self._value  # type: ignore[return-value]

            self._misses += 1
            value = compute()
            self._value = value
            self._cached_at = current_time
            return value

    def invalidate(self) -> None:
        """Test-only escape hatch, same rationale as RateLimiter.reset():
        keeps the test suite's many independent test functions from
        seeing each other's stale cached data through the shared
        process-wide singleton.
        """
        with self._lock:
            self._value = None
            self._cached_at = None

    @property
    def stats(self) -> TTLCacheStats:
        return TTLCacheStats(hits=self._hits, misses=self._misses)
