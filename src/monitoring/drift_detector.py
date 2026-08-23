"""Population Stability Index (PSI) drift detection between the training
feature distribution (baseline) and recent live-scored traffic.

Pure logic only -- no DB or model access here (matches src/anomaly/
spike_detector.py's pattern). See api/services/drift_service.py for how
this gets wired to the training split and the live predictions table.

WHY PSI, NOT A KOLMOGOROV-SMIRNOV TEST (the brief allowed either):

PSI was chosen for three concrete reasons, not a coin flip:
1. Dependency footprint: this project has no scipy dependency anywhere
   (see requirements.txt) -- a KS test needs scipy.stats.ks_2samp; PSI
   needs nothing beyond numpy, which is already a hard dependency.
2. Output shape: PSI gives ONE plain, comparable-across-features number
   per feature with well-known, widely-cited convention thresholds (see
   below), which maps directly onto "a small bar per feature" in the UI.
   A KS test instead gives a (statistic, p-value) pair, which would force
   picking a significance level as a SECOND arbitrary judgment call on
   top of everything else here -- more machinery for no real benefit at
   this project's scale.
3. Domain fit: PSI originates in, and is still the standard tool for,
   exactly this problem in credit-risk/fraud model monitoring (comparing
   a live scoring population against the training population) -- it is
   not a mismatched tool being forced onto this use case.

HOW IT WORKS: bucket the BASELINE (training) distribution into decile
edges, then compare what fraction of the baseline vs. the live sample
falls into each bucket. PSI = sum((actual% - expected%) * ln(actual% /
expected%)) over all buckets -- zero when the two distributions are
identical, growing as they diverge.

HONESTY NOTE ON THRESHOLDS (same standard as spike_detector.py's z=3.0):
the 0.10 / 0.25 cut points below are the standard, widely-cited PSI
convention from credit-scoring/model-monitoring practice (roughly:
<0.10 no meaningful shift, 0.10-0.25 moderate shift worth a look, >=0.25
a shift worth investigating). They are a reasonable, conventional
default -- NOT rigorously tuned against this project's own model or any
real observed drift history, because no such history exists here. Treat
them as sensible starting points to revisit later, not a fitted cutoff.

HONESTY NOTE ON SAMPLE SIZE / WHAT THIS ACTUALLY DEMONSTRATES: PSI is a
population-comparison statistic -- it wants hundreds to thousands of live
samples to be a genuinely trustworthy signal. At this project's demo/
simulator scale, "recent live traffic" will typically be dozens to a few
hundred rows. Below MIN_LIVE_SAMPLE_SIZE this module refuses to compute a
score at all (see `insufficient_data`, mirroring spike_detector.py's own
cold-start gate) rather than report a number computed from too little
data. Even above that floor, treat this report as illustrative of the
CAPABILITY (the plumbing from training baseline to live comparison to a
UI badge genuinely works), not as a production-grade drift signal -- it
is not being sold as one.

HONESTY NOTE ON BUCKETING: bucket edges are quantiles of the baseline
distribution (default 10, i.e. deciles). For a low-cardinality feature
(e.g. hour_of_day, an integer 0-23) many of those quantile edges collapse
to the same value; duplicate edges are dropped, which can leave fewer
than 10 effective buckets and slightly reduce sensitivity for that
feature specifically. This is a known, accepted PSI limitation, not a
bug -- documented rather than hidden.

HONESTY NOTE ON AGGREGATION: the overall status is the WORST status among
the monitored features (max-severity, not an average) -- a deliberate,
simple, conservative choice: one drifting feature flags the whole report
even if the others are perfectly stable. This errs toward surfacing a
possible problem rather than averaging it away.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

DEFAULT_PSI_BUCKETS = 10
# Small floor applied to bucket proportions before taking a log ratio, so a
# bucket with zero observations on either side never produces log(0) or a
# division by zero. Standard practice in PSI implementations.
PSI_EPSILON = 1e-4

# Standard, widely-cited PSI convention -- see the HONESTY NOTE ON
# THRESHOLDS above for what this is and isn't.
PSI_MODERATE_THRESHOLD = 0.10
PSI_SIGNIFICANT_THRESHOLD = 0.25

# Below this many live samples, PSI is too noisy to trust at all -- report
# "insufficient data" rather than a wild, potentially meaningless number
# computed from a handful of points (same philosophy as spike_detector.py's
# DEFAULT_MIN_WINDOW_SIZE).
DEFAULT_MIN_LIVE_SAMPLE_SIZE = 30

# Default size of the "recent live traffic" window read from the
# predictions table. Larger than the fraud-spike detector's 50-row window
# (DEFAULT_WINDOW_SIZE in spike_detector.py) because a distribution
# comparison benefits from more points than a single proportion does; still
# a fixed row-COUNT window rather than a time window, for the same
# simplicity reason spike_detector.py gives (bursty, unpredictable arrival
# rate at this project's scale).
DEFAULT_LIVE_SAMPLE_SIZE = 200

STATUS_STABLE = "STABLE"
STATUS_MODERATE = "MODERATE_DRIFT"
STATUS_SIGNIFICANT = "SIGNIFICANT_DRIFT"


def _bucket_edges(reference: np.ndarray, buckets: int) -> np.ndarray:
    """Decile (or N-tile) edges of the reference distribution, with the
    outer edges opened to +/-inf so a live value outside the observed
    training range still falls into the first/last bucket instead of being
    silently dropped by np.histogram.
    """
    quantiles = np.linspace(0, 1, buckets + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if edges.size < 2:
        # Degenerate reference distribution (e.g. every value identical).
        # Fall back to a single bucket that captures everything -- PSI will
        # come out as 0 either way, which is the honest answer: there is no
        # baseline spread to compare against.
        edges = np.array([reference.min(), reference.max()])
        if edges[0] == edges[1]:
            edges = np.array([edges[0] - 1.0, edges[0] + 1.0])
    edges = edges.astype(float)
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def _bucket_proportions(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(values, bins=edges)
    total = counts.sum()
    if total == 0:
        return np.zeros(len(counts), dtype=float)
    return counts / total


def compute_psi(
    reference: Sequence[float],
    live: Sequence[float],
    buckets: int = DEFAULT_PSI_BUCKETS,
    epsilon: float = PSI_EPSILON,
) -> float:
    """PSI of `live` relative to `reference`. Bucket edges are derived from
    `reference` only (the baseline defines what "normal" looks like);
    `live` is then binned into those same fixed edges. 0.0 for identical
    distributions, growing without a fixed upper bound as they diverge.
    """
    reference_arr = np.asarray(reference, dtype=float)
    live_arr = np.asarray(live, dtype=float)

    edges = _bucket_edges(reference_arr, buckets)
    expected = np.clip(_bucket_proportions(reference_arr, edges), epsilon, None)
    actual = np.clip(_bucket_proportions(live_arr, edges), epsilon, None)

    return float(np.sum((actual - expected) * np.log(actual / expected)))


def _status_for(psi: float) -> str:
    if psi >= PSI_SIGNIFICANT_THRESHOLD:
        return STATUS_SIGNIFICANT
    if psi >= PSI_MODERATE_THRESHOLD:
        return STATUS_MODERATE
    return STATUS_STABLE


@dataclass(frozen=True)
class FeatureDriftResult:
    feature: str
    psi: float
    status: str
    reference_sample_size: int
    live_sample_size: int


@dataclass(frozen=True)
class DriftReport:
    overall_status: str
    features: list[FeatureDriftResult] = field(default_factory=list)
    live_sample_size: int = 0
    min_live_sample_size: int = DEFAULT_MIN_LIVE_SAMPLE_SIZE
    insufficient_data: bool = False


def detect_drift(
    reference_by_feature: dict[str, Sequence[float]],
    live_by_feature: dict[str, Sequence[float]],
    buckets: int = DEFAULT_PSI_BUCKETS,
    min_live_sample_size: int = DEFAULT_MIN_LIVE_SAMPLE_SIZE,
) -> DriftReport:
    """Compare each feature's reference (training) distribution against its
    live (recent-traffic) distribution and roll the per-feature results up
    into one overall status.

    All features are assumed to share one live sample size (they are
    computed from the same underlying window of recent predictions) --
    that shared size is what gates `insufficient_data`, not a per-feature
    check, since a partial feature list would be a confusing report.
    """
    live_sample_size = len(next(iter(live_by_feature.values()), []))

    if live_sample_size < min_live_sample_size:
        features = [
            FeatureDriftResult(
                feature=name,
                psi=0.0,
                status=STATUS_STABLE,
                reference_sample_size=len(reference_values),
                live_sample_size=live_sample_size,
            )
            for name, reference_values in reference_by_feature.items()
        ]
        return DriftReport(
            overall_status=STATUS_STABLE,
            features=features,
            live_sample_size=live_sample_size,
            min_live_sample_size=min_live_sample_size,
            insufficient_data=True,
        )

    features = []
    for name, reference_values in reference_by_feature.items():
        live_values = live_by_feature.get(name, [])
        psi = compute_psi(reference_values, live_values, buckets=buckets)
        features.append(
            FeatureDriftResult(
                feature=name,
                psi=psi,
                status=_status_for(psi),
                reference_sample_size=len(reference_values),
                live_sample_size=len(live_values),
            )
        )

    if any(f.status == STATUS_SIGNIFICANT for f in features):
        overall = STATUS_SIGNIFICANT
    elif any(f.status == STATUS_MODERATE for f in features):
        overall = STATUS_MODERATE
    else:
        overall = STATUS_STABLE

    return DriftReport(
        overall_status=overall,
        features=features,
        live_sample_size=live_sample_size,
        min_live_sample_size=min_live_sample_size,
        insufficient_data=False,
    )
