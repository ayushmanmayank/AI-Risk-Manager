"""One-command demo reset: brings the system from ANY current state (fresh,
mid-demo, exhausted HIGH-row pool, partially seeded, whatever) to a known-
good, demo-ready starting point.

WHY THIS EXISTS: the Day 13 audit found that manually chasing calm/seeded
state before a demo was fragile in two ways -- seed_chargebacks.py fails
outright on a DB with no prior predictions, and simulate.py --spike bursts
consume a fixed, finite pool of high-probability test rows via content-hash
dedup, which "use a bigger --spike-size" only delays running out of, it
never actually fixes.

WHAT THIS DOES NOT TOUCH: data/processed/features.csv (the scored test
split) and models/fraud_model_v1.pkl are read-only inputs to every
prediction ever made by this system -- nothing here, or anywhere else in
the app, ever writes to either. The "40-row HIGH-probability pool" that
ran out during the Day 13 audit is not a resource in those files that
depletes -- it is purely a bookkeeping artifact of which rows already
exist as ROWS IN THE PREDICTIONS TABLE (content-hash dedup only checks
that table). Clearing the predictions table (step 1 below) throws that
bookkeeping away entirely, so every single row in features.csv -- all 40
of the HIGH ones included -- is "fresh" again immediately after a reset,
with no dependency on how much of the pool was consumed before.

ORDER OF OPERATIONS, and why each step is where it is:

  1. Clear predictions, alerts, chargebacks, refunds. This alone already
     restores the full content-hash dedup pool (see above) -- everything
     after this step is building fresh demo-ready state on top of a
     genuinely empty table, not working around leftover state.

  2. Seed a *small* amount of baseline traffic: a few of the highest-
     probability rows (HIGH tier) plus a larger random sample of ordinary
     rows (LOW tier, by far the common case in this dataset). This is
     necessary before step 3 -- seed_chargebacks.py legitimately refuses
     to invent chargebacks against transactions that don't exist yet (see
     its own docstring: every fact must trace to a real record), so it
     needs at least one real HIGH and one real LOW prediction already
     stored. Only a handful of HIGH rows are used here (BASELINE_HIGH_COUNT,
     default 3 -- exactly what seed_chargebacks.py's "3 HIGH picks" story
     needs), deliberately leaving the other ~37 of the 40-row pool
     completely untouched for the live --spike moment during the actual
     demo.

  3. Seed chargebacks against that baseline. Guaranteed to succeed now,
     since step 2 ensured both a HIGH and a LOW prediction already exist.

  4. Push a larger cooldown batch of ordinary traffic
     (COOLDOWN_COUNT >= the spike detector's own rolling window size).
     The HIGH rows seeded in step 2 are recent enough to still count
     toward the rolling window's fraud rate right after step 3 -- on
     their own they would likely already read as an active spike (as
     little as 1 HIGH in a small recent window can cross the z-test
     threshold; see src/anomaly/spike_detector.py's own docstring on
     this sensitivity). Adding at least a full window's worth of
     ordinary traffic afterward pushes those HIGH rows out of the
     "most recent N" window entirely, by construction -- this is a
     deterministic guarantee from the window size, not a probabilistic
     hope.

  5. Verify -- not assume -- the resulting alert status is actually calm,
     and report the real number either way.

Usage:
    python scripts/reset_demo_data.py
    python scripts/reset_demo_data.py --api-url http://localhost:8000/api/v1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402
import pandas as pd  # noqa: E402

import api.services.db as db_module  # noqa: E402
from api.services.db_models import (  # noqa: E402
    AlertRecord,
    ChargebackRecord,
    PredictionRecord,
    RefundRecord,
)
from simulator.simulate import load_test_split, rank_by_fraud_probability, to_payload  # noqa: E402
from src.anomaly.spike_detector import DEFAULT_WINDOW_SIZE  # noqa: E402
from src.evidence.seed_chargebacks import seed as seed_chargebacks  # noqa: E402

DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1"

# Exactly what seed_chargebacks.py's "3 HIGH picks" story needs -- kept
# minimal so the vast majority of the 40-row HIGH pool stays untouched for
# the live demo's own --spike moment.
BASELINE_HIGH_COUNT = 3
# Comfortably more than seed_chargebacks.py's "3 LOW picks + 1 extra" need;
# also what makes the Dashboard look like something real happened, not an
# empty shell.
BASELINE_NORMAL_COUNT = 15
# Must be >= DEFAULT_WINDOW_SIZE to *guarantee* (not merely make likely)
# that the baseline HIGH rows above age out of the rolling window.
COOLDOWN_COUNT = DEFAULT_WINDOW_SIZE


def clear_demo_tables(session_factory=None) -> dict[str, int]:
    """Empties predictions/alerts/chargebacks/refunds via the SAME live
    SQLAlchemy session factory the running API uses (looked up through the
    module, not imported by value, so this respects test-time DB
    monkeypatching exactly like the app's own routes do -- see
    src/evidence/seed_chargebacks.py's history for why that distinction
    matters).

    Deliberately does NOT touch data/processed/features.csv or
    models/fraud_model_v1.pkl -- see module docstring.
    """
    factory = session_factory or db_module.SessionLocal
    session = factory()
    try:
        counts = {
            "chargebacks": session.query(ChargebackRecord).delete(),
            "refunds": session.query(RefundRecord).delete(),
            "alerts": session.query(AlertRecord).delete(),
            "predictions": session.query(PredictionRecord).delete(),
        }
        session.commit()
        return counts
    finally:
        session.close()


def _send_batch(client: httpx.Client, api_url: str, rows: pd.DataFrame) -> tuple[int, int]:
    """Quiet batch sender for this script's own use (unlike
    simulate.py's send_transaction, which narrates each row for a human
    audience -- this reports one summary instead of dozens of lines).
    Returns (succeeded, failed).
    """
    succeeded = 0
    failed = 0
    for _, row in rows.iterrows():
        payload = to_payload(row)
        try:
            response = client.post(f"{api_url}/predict", json=payload, timeout=10.0)
        except httpx.RequestError as exc:
            print(f"  WARNING: request failed: {exc}")
            failed += 1
            continue
        if response.status_code not in (200, 201):
            print(f"  WARNING: HTTP {response.status_code}: {response.text}")
            failed += 1
            continue
        succeeded += 1
    return succeeded, failed


def reset_demo_data(
    client: httpx.Client,
    api_url: str = DEFAULT_API_URL,
    baseline_high_count: int = BASELINE_HIGH_COUNT,
    baseline_normal_count: int = BASELINE_NORMAL_COUNT,
    cooldown_count: int = COOLDOWN_COUNT,
    seed: int | None = None,
    session_factory=None,
) -> dict:
    """The full reset. See module docstring for the exact order of
    operations and why each step is necessary. Returns a summary dict
    (also used directly by tests/test_reset_script.py).
    """
    started = time.perf_counter()

    cleared = clear_demo_tables(session_factory)

    test_data = load_test_split()
    ranked = rank_by_fraud_probability(test_data)
    high_rows = ranked.sort_values("_fraud_probability", ascending=False).head(baseline_high_count)
    normal_rows = test_data.sample(n=baseline_normal_count, random_state=seed)

    high_ok, high_failed = _send_batch(client, api_url, high_rows)
    normal_ok, normal_failed = _send_batch(client, api_url, normal_rows)

    seed_chargebacks(reset=False)

    cooldown_seed = (seed + 1) if seed is not None else None
    cooldown_rows = test_data.sample(n=cooldown_count, random_state=cooldown_seed)
    cooldown_ok, cooldown_failed = _send_batch(client, api_url, cooldown_rows)

    alerts_response = client.get(f"{api_url}/alerts", timeout=10.0)
    alerts_response.raise_for_status()
    alert_status = alerts_response.json()

    elapsed = time.perf_counter() - started

    return {
        "cleared": cleared,
        "baseline_high_sent": high_ok,
        "baseline_high_failed": high_failed,
        "baseline_normal_sent": normal_ok,
        "baseline_normal_failed": normal_failed,
        "cooldown_sent": cooldown_ok,
        "cooldown_failed": cooldown_failed,
        "is_spike_active_after_reset": alert_status["is_spike_active"],
        "window_size_after_reset": alert_status["window_size"],
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"Base API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for baseline/cooldown sampling")
    args = parser.parse_args()

    with httpx.Client() as client:
        try:
            health = client.get(f"{args.api_url}/health", timeout=5.0)
            health.raise_for_status()
        except httpx.HTTPError as exc:
            sys.exit(f"Backend not reachable at {args.api_url}: {exc}\nRun `docker compose up -d` first.")

        summary = reset_demo_data(client, api_url=args.api_url, seed=args.seed)

    print("=== Demo reset complete ===")
    print(f"Cleared: {summary['cleared']}")
    print(
        f"Baseline seeded: {summary['baseline_high_sent']} HIGH + "
        f"{summary['baseline_normal_sent']} normal "
        f"(failures: {summary['baseline_high_failed'] + summary['baseline_normal_failed']})"
    )
    print(f"Chargebacks seeded against that baseline.")
    print(f"Cooldown: {summary['cooldown_sent']} more transactions (flushes HIGH rows out of the rolling window)")
    calm = not summary["is_spike_active_after_reset"]
    print(f"Spike detector calm after reset: {calm}  (window size: {summary['window_size_after_reset']})")
    print(f"Total time: {summary['elapsed_seconds']:.2f}s")
    if not calm:
        print(
            "WARNING: spike still shows active after reset -- this should not happen given "
            "cooldown_count >= the detector's window size. Investigate before demoing."
        )


if __name__ == "__main__":
    main()
