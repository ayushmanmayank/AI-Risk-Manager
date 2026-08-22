"""Rolling fraud-rate spike / anomaly detector.

Pure logic only -- no DB or model access here (matches src/risk/*'s
pattern). See api/services/anomaly_service.py for how this gets wired to
live prediction data and a persisted alerts table.

DESIGN DECISIONS (be explicit, per the Day 7 brief):

Windowing: a fixed COUNT window (last N=50 predictions), not a time
window (last N minutes). Chosen because it's simpler given current
storage: predictions arrive at an unpredictable, bursty pace (a hackathon
demo can go quiet for a minute, or the simulator can burst 5 in 1.5
seconds), so a wall-clock window means reasoning about gaps and arrival
rate; a count window sidesteps that entirely and is trivial to query
("last N rows by timestamp").

current_fraud_rate definition: the fraction of the most recent N
predictions whose risk_tier == "HIGH" -- NOT "fraud_probability above a
threshold". Reusing risk_tier keeps this consistent with the HIGH tier
already shown everywhere else in the product (dashboard, transaction
list, decision engine); introducing a second, independent probability
cutoff here would silently drift out of sync with
src/risk/decision_engine.py's high_threshold if that default ever changes.

baseline_fraud_rate definition: the model's own predicted HIGH-tier rate
on the TRAINING split (never validation/test), not the raw ground-truth
Class fraud rate. Those two are close but not identical (0.198% vs 0.193%
on this dataset's training split) because the model has both false
positives and false negatives -- comparing a model-predicted
current_fraud_rate against a ground-truth baseline would be a subtle
apples-to-oranges mismatch. See api/services/anomaly_service.py for where
this gets computed (scoring 199k rows takes well under a second).
A live rolling baseline (recomputed from recent-but-older live traffic)
was the other option the brief allowed; it was rejected here because
hackathon-scale live traffic will almost always be too sparse for a
second window to be meaningful, and a live baseline risks being silently
contaminated by an earlier undetected spike, making the detector
progressively blind to real ones. A large, fixed, known-clean training
sample avoids both problems.

Statistical test: a one-sample proportion z-test. Under the null
hypothesis that the current window's true HIGH rate equals the baseline
rate p0, the standard error of an n-sample proportion is
sqrt(p0*(1-p0)/n), so z = (current_rate - p0) / standard_error. This is
the same test the "3+ standard deviations above baseline" framing in the
brief maps onto directly.

HONESTY NOTE ON THRESHOLDS (see also the Day 7 report): the z=3.0
spike cutoff and the LOW/MEDIUM/HIGH severity bands below are reasonable,
round, conventional choices (3-sigma is a standard "notable deviation"
convention) -- they are NOT statistically derived from any labeled
history of real fraud spikes, because no such history exists for this
project. Treat them as sensible defaults to tune later against real
incident data, not as a rigorously fitted threshold.

HONESTY NOTE ON SENSITIVITY: because baseline_fraud_rate is so low
(~0.2%), the z-test is inherently very sensitive -- a single genuine HIGH
prediction landing in a modest window (e.g. 1 in 10) can already produce
a z-score past the spike threshold. This is mathematically correct (that
really is a rare event under the baseline rate), not a bug, but it does
mean "is_spike=True" does not strictly require a multi-transaction burst
pattern -- one true positive in a quiet window can trigger it too.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_WINDOW_SIZE = 50
# Below this many predictions in the window, the proportion estimate is
# too noisy to trust at all -- report "no data" rather than a wild,
# potentially nonsensical z-score computed from a handful of points.
DEFAULT_MIN_WINDOW_SIZE = 10
DEFAULT_Z_SPIKE_THRESHOLD = 3.0
# z-score cut points for severity bands. Manually chosen, not fitted --
# see the HONESTY NOTE above.
SEVERITY_THRESHOLDS: dict[str, float] = {"HIGH": 8.0, "MEDIUM": 5.0, "LOW": 3.0}

HIGH_RISK_TIER = "HIGH"
SEVERITY_NONE = "NONE"


@dataclass(frozen=True)
class SpikeDetectionResult:
    anomaly_score: float
    is_spike: bool
    current_fraud_rate: float
    baseline_fraud_rate: float
    severity: str
    window_size: int
    high_count: int
    insufficient_data: bool


def detect_spike(
    recent_risk_tiers: list[str],
    baseline_fraud_rate: float,
    z_spike_threshold: float = DEFAULT_Z_SPIKE_THRESHOLD,
    min_window_size: int = DEFAULT_MIN_WINDOW_SIZE,
) -> SpikeDetectionResult:
    """Evaluate the most recent window of predictions for a fraud-rate spike.

    `recent_risk_tiers` should be the last N predictions' risk_tier values,
    most-recent-first or in any order (order doesn't matter here, only
    composition). `baseline_fraud_rate` is the reference HIGH-tier rate to
    compare against (see module docstring for what it should be).
    """
    n = len(recent_risk_tiers)
    high_count = sum(1 for tier in recent_risk_tiers if tier == HIGH_RISK_TIER)
    current_fraud_rate = (high_count / n) if n else 0.0

    if n < min_window_size:
        return SpikeDetectionResult(
            anomaly_score=0.0,
            is_spike=False,
            current_fraud_rate=current_fraud_rate,
            baseline_fraud_rate=baseline_fraud_rate,
            severity=SEVERITY_NONE,
            window_size=n,
            high_count=high_count,
            insufficient_data=True,
        )

    p0 = baseline_fraud_rate
    variance = p0 * (1 - p0) / n
    standard_error = math.sqrt(variance) if variance > 0 else 0.0

    if standard_error == 0:
        # Degenerate baseline (p0 is exactly 0 or 1). Fall back to a plain
        # presence check rather than dividing by zero.
        z = float(high_count) * z_spike_threshold if high_count > 0 else 0.0
    else:
        z = (current_fraud_rate - p0) / standard_error

    # Only an INCREASE in fraud rate counts as a spike; a rate below
    # baseline is not anomalous for this detector's purpose.
    z = max(z, 0.0)

    return SpikeDetectionResult(
        anomaly_score=z,
        is_spike=z >= z_spike_threshold,
        current_fraud_rate=current_fraud_rate,
        baseline_fraud_rate=baseline_fraud_rate,
        severity=_severity_for(z),
        window_size=n,
        high_count=high_count,
        insufficient_data=False,
    )


def _severity_for(z: float) -> str:
    if z >= SEVERITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    if z >= SEVERITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    if z >= SEVERITY_THRESHOLDS["LOW"]:
        return "LOW"
    return SEVERITY_NONE
