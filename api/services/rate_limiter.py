"""A small in-memory, per-key sliding-window rate limiter.

WHY HAND-ROLLED, NOT `slowapi` (the brief allowed either): this project
has zero rate-limiting dependency today, and `slowapi` pulls in the
`limits` package plus a storage backend abstraction built for exactly the
thing this project explicitly doesn't have yet -- multiple processes/
replicas needing SHARED limiter state (see the HONESTY NOTE below). For a
single-process hackathon deployment, a ~40-line sliding-window log is
easier to read, easier to unit-test deterministically (no library
internals to mock), and adds no new dependency -- the same "keep it
simple, don't overbuild" call this project already made for PSI over a
KS-test dependency (src/monitoring/drift_detector.py) and for the
hand-rolled z-test over a stats-library spike detector
(src/anomaly/spike_detector.py). If this ever needs to work across
multiple replicas, the fix is the same one named in README's Production
Considerations section: move this state to Redis, not swap libraries.

ALGORITHM: sliding-window log, not a fixed-window counter. A fixed window
("60 requests since the top of this minute") allows up to 2x the stated
rate in a burst straddling a window boundary (60 requests at 0:59, 60
more at 1:00). A sliding window log timestamps every request and only
counts the ones still inside the trailing `window_seconds`, so the limit
is honest at every point in time, not just at window edges. The
tradeoff -- O(requests-in-window) memory per key instead of O(1) -- is
irrelevant at hackathon request volumes.

HONESTY NOTE: this state lives in one process's memory. It is correct
and sufficient for this project's actual deployment (single uvicorn
process, no --workers flag -- see the Dockerfile), but would NOT
correctly enforce a global limit across multiple replicas behind a load
balancer, since each replica would track its own separate counts. That
scaling gap is named explicitly, not silently, in README's Production
Considerations section.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

DEFAULT_MAX_REQUESTS = 60
DEFAULT_WINDOW_SECONDS = 60.0


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: float


class RateLimiter:
    """Per-key sliding-window request limiter. One instance per limited
    endpoint (or shared across endpoints that should share a budget) --
    each instance owns its own independent set of per-key windows.
    """

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> RateLimitResult:
        """Record and evaluate one request for `key` (e.g. a client IP).
        Call once per incoming request -- this both checks AND counts the
        request in the same call, so a rejected request is not itself
        counted against the caller's budget (see the < vs <= choice below).
        `now` is injectable for deterministic tests; defaults to
        `time.monotonic()` (wall-clock-independent, immune to system clock
        adjustments during a long-running process).
        """
        current_time = time.monotonic() if now is None else now
        cutoff = current_time - self.window_seconds

        with self._lock:
            hits = self._hits.setdefault(key, [])
            # Drop timestamps that have aged out of the window. `hits` is
            # append-only-then-trimmed, so it stays sorted -- a simple
            # index scan from the front is enough, no need to re-sort.
            i = 0
            while i < len(hits) and hits[i] < cutoff:
                i += 1
            if i:
                del hits[:i]

            if len(hits) >= self.max_requests:
                retry_after = (hits[0] + self.window_seconds) - current_time
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=max(0.0, retry_after),
                )

            hits.append(current_time)
            return RateLimitResult(
                allowed=True,
                remaining=self.max_requests - len(hits),
                retry_after_seconds=0.0,
            )

    def reset(self) -> None:
        """Clears all tracked state -- test-only escape hatch so the test
        suite's many /predict calls don't bleed into each other's request
        budgets across test functions sharing the process-wide singleton.
        """
        with self._lock:
            self._hits.clear()
