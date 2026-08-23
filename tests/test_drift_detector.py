"""Tests for the Tier 3B PSI-based drift detector
(src/monitoring/drift_detector.py).

Uses a fixed synthetic reference distribution rather than the real
features.csv/model bundle -- this module's job is pure statistics, and
these tests exercise that logic directly, the same way test_anomaly.py
tests detect_spike() without touching the real trained model.

Each test builds its own independently-seeded RNG rather than sharing one
module-level generator, so results are deterministic regardless of test
execution order.
"""

from __future__ import annotations

import numpy as np

from src.monitoring.drift_detector import (
    DEFAULT_MIN_LIVE_SAMPLE_SIZE,
    PSI_MODERATE_THRESHOLD,
    PSI_SIGNIFICANT_THRESHOLD,
    compute_psi,
    detect_drift,
)


def _reference_bundle(seed: int, n: int = 5_000) -> dict[str, list[float]]:
    """A small stand-in for the four monitored features, each drawn from
    its own fixed distribution -- not the real training data, just
    something with real spread to bucket against.
    """
    rng = np.random.default_rng(seed)
    return {
        "Amount": rng.normal(50.0, 20.0, n).tolist(),
        "amount_zscore": rng.normal(0.0, 1.0, n).tolist(),
        "hour_of_day": rng.integers(0, 24, n).astype(float).tolist(),
        "fraud_probability": rng.beta(1.5, 50, n).tolist(),
    }


def test_identical_distribution_reports_stable():
    # Live traffic drawn from the same distribution family as the baseline
    # (different draw, same parameters) -- the honest no-drift case.
    reference = _reference_bundle(seed=1)
    live = _reference_bundle(seed=2, n=500)
    report = detect_drift(reference, live)

    assert report.overall_status == "STABLE"
    assert report.insufficient_data is False
    assert all(f.status == "STABLE" for f in report.features)
    assert all(f.psi < PSI_MODERATE_THRESHOLD for f in report.features)


def test_shifted_distribution_reports_drift():
    # Live Amount traffic is a completely different, non-overlapping
    # distribution (mean shifted from 50 to 500, tighter spread) --
    # deliberately extreme so this is unambiguous, not a borderline case.
    reference = _reference_bundle(seed=3)
    live = _reference_bundle(seed=4, n=500)
    live["Amount"] = np.random.default_rng(5).normal(500.0, 10.0, 500).tolist()

    report = detect_drift(reference, live)

    amount_result = next(f for f in report.features if f.feature == "Amount")
    assert amount_result.status == "SIGNIFICANT_DRIFT"
    assert amount_result.psi >= PSI_SIGNIFICANT_THRESHOLD
    # One drifting feature must flag the whole report (max-severity
    # aggregation -- see the module docstring's HONESTY NOTE ON AGGREGATION).
    assert report.overall_status == "SIGNIFICANT_DRIFT"
    # The untouched features must NOT be dragged along -- this isn't a
    # single blended score.
    other_features = [f for f in report.features if f.feature != "Amount"]
    assert all(f.status == "STABLE" for f in other_features)


def test_moderately_shifted_distribution_reports_moderate_not_significant():
    # A real but modest shift (mean 50 -> 57, same spread) should land in
    # the middle band, not either extreme -- confirms the detector is
    # graded, not just a binary trigger. Verified by direct computation
    # (PSI ~0.17 for this exact seed/shift combination), not assumed.
    reference = _reference_bundle(seed=1)
    live = _reference_bundle(seed=2, n=800)
    live["Amount"] = np.random.default_rng(3).normal(57.0, 20.0, 800).tolist()

    report = detect_drift(reference, live)
    amount_result = next(f for f in report.features if f.feature == "Amount")

    assert PSI_MODERATE_THRESHOLD <= amount_result.psi < PSI_SIGNIFICANT_THRESHOLD
    assert amount_result.status == "MODERATE_DRIFT"
    assert report.overall_status == "MODERATE_DRIFT"


def test_cold_start_very_little_live_data_does_not_crash():
    # Only a handful of live-scored predictions so far -- far below
    # DEFAULT_MIN_LIVE_SAMPLE_SIZE. Must report insufficient_data, not a
    # wild PSI number computed from noise, and must not raise.
    reference = _reference_bundle(seed=1)
    live = {
        "Amount": [42.0, 17.5, 90.0],
        "amount_zscore": [0.1, -0.2, 1.5],
        "hour_of_day": [10.0, 11.0, 12.0],
        "fraud_probability": [0.01, 0.02, 0.03],
    }
    assert len(live["Amount"]) < DEFAULT_MIN_LIVE_SAMPLE_SIZE

    report = detect_drift(reference, live)

    assert report.insufficient_data is True
    assert report.overall_status == "STABLE"
    assert all(f.psi == 0.0 for f in report.features)
    assert report.live_sample_size == 3


def test_cold_start_zero_live_data_does_not_crash():
    reference = _reference_bundle(seed=1)
    live = {name: [] for name in reference}

    report = detect_drift(reference, live)

    assert report.insufficient_data is True
    assert report.live_sample_size == 0
    assert report.overall_status == "STABLE"


def test_compute_psi_is_zero_for_identical_arrays():
    values = np.random.default_rng(6).normal(size=1_000).tolist()
    assert compute_psi(values, values) == 0.0


def test_compute_psi_increases_with_severity_of_shift():
    # A continuous statistic, not just a threshold trigger -- mirrors
    # test_anomaly.py's test_anomaly_score_responds_proportionally.
    reference = np.random.default_rng(7).normal(0.0, 1.0, 3_000).tolist()
    mild_shift = np.random.default_rng(8).normal(0.3, 1.0, 500).tolist()
    severe_shift = np.random.default_rng(9).normal(3.0, 1.0, 500).tolist()

    psi_mild = compute_psi(reference, mild_shift)
    psi_severe = compute_psi(reference, severe_shift)

    assert 0.0 < psi_mild < psi_severe


def test_degenerate_reference_distribution_does_not_crash():
    # Every reference value identical -- an edge case the bucket-edge
    # logic must handle without dividing by zero or crashing.
    reference = {"constant_feature": [5.0] * 200}
    live = {"constant_feature": [5.0] * 50 + [6.0] * 50}

    report = detect_drift(reference, live)

    assert report.insufficient_data is False
    feature_result = report.features[0]
    assert not np.isnan(feature_result.psi)
    assert not np.isinf(feature_result.psi)
