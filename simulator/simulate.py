"""Real-time transaction simulator for live demos.

*** This replays REAL historical transactions, not synthetic/fabricated
*** data. Every row sent is a genuine transaction from the held-out TEST
*** split of data/processed/features.csv -- the same split boundary
*** src/models/train_fraud_model.py used, taken directly from the trained
*** model's stored split_indices so it's guaranteed to match. The model was
*** never trained OR validated on these rows, so replaying them live is not
*** "cheating" -- it's genuinely held-out data, scored for the first time
*** by the running API at demo time.

What "live" actually means here: each row's own Time/Amount/V1-V28 values
are sent completely unchanged. Time is dataset-relative seconds since the
first transaction, and must stay untouched for feature engineering (e.g.
hour_of_day, amount_zscore) to compute correctly -- faking it to "now" in
seconds-since-epoch would silently break every derived feature. What
*does* become "now" is the prediction's stored `timestamp`: the API always
assigns that server-side, at the moment each POST /predict actually lands
(see api/services/risk_service.py:evaluate_transaction). So the dashboard
and transaction list will correctly show fresh, current timestamps for
every replayed row, even though the underlying transaction content is
historical -- exactly the "live traffic" look this script exists to produce.

Explicitly NOT in scope here: fraud-spike DETECTION (an anomaly engine
that would notice and flag --spike's burst). This script only generates
traffic; noticing it is a separate, not-yet-built feature.

Usage:
    python simulator/simulate.py --count 12
    python simulator/simulate.py --count 8 --spike --spike-size 5
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx
import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_model_v1.pkl"
RAW_FEATURE_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]

DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_INTERVAL_SECONDS = 2.5
DEFAULT_COUNT = 12
DEFAULT_SPIKE_SIZE = 5
DEFAULT_SPIKE_INTERVAL_SECONDS = 0.3

# Plain ASCII only -- Windows consoles commonly default to a cp1252
# codepage that cannot encode emoji, and this script needs to run cleanly
# during a live demo, not crash on a narrator's terminal.
TIER_MARKER = {"LOW": "   ", "MEDIUM": " ! ", "HIGH": "!!!"}


def load_test_split() -> pd.DataFrame:
    """The genuinely held-out slice: same boundary the trained model itself
    recorded (bundle['split_indices']), not recomputed from scratch, so this
    can never drift from what the model was actually evaluated against.
    """
    if not MODEL_PATH.exists():
        sys.exit(f"Model not found at {MODEL_PATH}. Run src/models/train_fraud_model.py first.")
    if not FEATURES_PATH.exists():
        sys.exit(f"Features not found at {FEATURES_PATH}. Run src/features/build_features.py first.")

    bundle = joblib.load(MODEL_PATH)
    data = pd.read_csv(FEATURES_PATH).sort_values("Time", kind="stable").reset_index(drop=True)
    test_start = bundle["split_indices"]["validation_end"]
    return data.iloc[test_start:].reset_index(drop=True)


def rank_by_fraud_probability(test_data: pd.DataFrame) -> pd.DataFrame:
    """Score the test set with the local model (not the API) purely to pick
    illustrative high-probability rows for --spike. This is choosing which
    real rows to replay for a demo, not tuning or evaluating the model --
    no metric from this ranking is reported anywhere.
    """
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    cols = bundle["feature_columns"]
    probabilities = model.predict_proba(test_data[cols])[:, 1]
    return test_data.assign(_fraud_probability=probabilities)


def to_payload(row: pd.Series) -> dict:
    return {column: float(row[column]) for column in RAW_FEATURE_COLUMNS}


def send_transaction(client: httpx.Client, api_url: str, row: pd.Series, label: str, index: int) -> None:
    payload = to_payload(row)
    try:
        response = client.post(f"{api_url}/predict", json=payload, timeout=10.0)
    except httpx.RequestError as exc:
        print(f"  [{label} #{index}] ERROR: could not reach API at {api_url} ({exc})")
        return

    if response.status_code not in (200, 201):
        print(f"  [{label} #{index}] ERROR: HTTP {response.status_code} -- {response.text}")
        return

    body = response.json()
    tier = body["risk_tier"]
    marker = TIER_MARKER.get(tier, "   ")
    reused = " (duplicate content -> existing prediction reused)" if response.status_code == 200 else ""
    print(
        f"  [{label} #{index:>2}] {marker} amount=${body['amount']:>9,.2f}  "
        f"fraud_probability={body['fraud_probability']:>7.2%}  "
        f"risk_tier={tier:<6}  decision={body['decision']:<6}  "
        f"expected_loss=${body['expected_loss']:>9,.2f}{reused}"
    )


def run_normal_stream(client: httpx.Client, api_url: str, rows: pd.DataFrame, interval: float) -> None:
    print(f"\n--- Replaying {len(rows)} real held-out transactions (~{interval}s apart) ---")
    print("    [REPLAYED REAL DATA -- from the held-out test split, not fabricated]\n")
    for i, (_, row) in enumerate(rows.iterrows(), start=1):
        send_transaction(client, api_url, row, label="normal", index=i)
        if i < len(rows):
            time.sleep(interval)


def run_spike_burst(client: httpx.Client, api_url: str, rows: pd.DataFrame, interval: float) -> None:
    print(f"\n--- [SPIKE] bursting {len(rows)} real high-fraud-probability transactions (~{interval}s apart) ---")
    print("    [REPLAYED REAL DATA -- genuine high-probability rows from the held-out test split]")
    print("    [This script only GENERATES the burst. Spike DETECTION is a separate, not-yet-built feature.]\n")
    for i, (_, row) in enumerate(rows.iterrows(), start=1):
        send_transaction(client, api_url, row, label="spike", index=i)
        if i < len(rows):
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"Base API URL (default: {DEFAULT_API_URL})")
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL_SECONDS,
        help=f"Seconds between normal-stream transactions (default: {DEFAULT_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT,
        help=f"Number of normal transactions to replay (default: {DEFAULT_COUNT})",
    )
    parser.add_argument("--spike", action="store_true", help="After the normal stream, burst real high-fraud-probability rows")
    parser.add_argument(
        "--spike-size", type=int, default=DEFAULT_SPIKE_SIZE,
        help=f"Number of rows in the spike burst (default: {DEFAULT_SPIKE_SIZE})",
    )
    parser.add_argument(
        "--spike-interval", type=float, default=DEFAULT_SPIKE_INTERVAL_SECONDS,
        help=f"Seconds between spike-burst transactions (default: {DEFAULT_SPIKE_INTERVAL_SECONDS})",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible normal-stream sampling")
    args = parser.parse_args()

    test_data = load_test_split()
    print(f"Loaded {len(test_data):,} real held-out test-split transactions from {FEATURES_PATH.name}")

    sample = test_data.sample(n=min(args.count, len(test_data)), random_state=args.seed)

    with httpx.Client() as client:
        try:
            health = client.get(f"{args.api_url}/health", timeout=5.0)
            health.raise_for_status()
        except httpx.HTTPError as exc:
            sys.exit(f"API not reachable at {args.api_url}: {exc}")

        run_normal_stream(client, args.api_url, sample, args.interval)

        if args.spike:
            ranked = rank_by_fraud_probability(test_data)
            spike_rows = ranked.sort_values("_fraud_probability", ascending=False).head(args.spike_size)
            run_spike_burst(client, args.api_url, spike_rows, args.spike_interval)

    print("\nDone. Check GET /api/v1/analytics or the dashboard for the updated totals.")


if __name__ == "__main__":
    main()
