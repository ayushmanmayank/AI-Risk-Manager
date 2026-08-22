"""Tests for the Day 7 rolling fraud-rate spike detector.

Uses BASELINE_RATE = 0.00198, the actual model-predicted HIGH-tier rate on
the training split (see api/services/anomaly_service.py), so these tests
exercise the detector against the real baseline this project uses, not an
arbitrary round number.
"""

from __future__ import annotations

from src.anomaly.spike_detector import (
    DEFAULT_MIN_WINDOW_SIZE,
    DEFAULT_WINDOW_SIZE,
    detect_spike,
)

BASELINE_RATE = 0.00198


def _window(high_count: int, total: int) -> list[str]:
    return ["HIGH"] * high_count + ["LOW"] * (total - high_count)


def test_normal_stable_rate_does_not_trigger_spike():
    # 50 predictions, zero HIGH -- the quiet, no-fraud-seen baseline case.
    result = detect_spike(_window(0, 50), baseline_fraud_rate=BASELINE_RATE)
    assert result.is_spike is False
    assert result.severity == "NONE"
    assert result.current_fraud_rate == 0.0
    assert result.anomaly_score == 0.0


def test_one_stray_high_in_a_full_window_does_not_trigger():
    # 1/50 (2%) is elevated vs. baseline (~0.2%) but is ordinary noise, not
    # the multi-transaction burst pattern --spike produces. z ~= 2.87,
    # just under the 3.0 cutoff -- verified by direct computation, not
    # assumed.
    result = detect_spike(_window(1, 50), baseline_fraud_rate=BASELINE_RATE)
    assert result.is_spike is False
    assert result.severity == "NONE"
    assert result.current_fraud_rate == 0.02


def test_genuine_spike_matching_simulator_burst_triggers():
    # Matches simulate.py --spike's actual shape: ~45 normal + 5 HIGH burst
    # in a 50-window.
    result = detect_spike(_window(5, 50), baseline_fraud_rate=BASELINE_RATE)
    assert result.is_spike is True
    assert result.severity in {"LOW", "MEDIUM", "HIGH"}
    assert result.anomaly_score >= 3.0
    assert result.current_fraud_rate == 0.10


def test_cold_start_few_predictions_does_not_crash_or_false_positive():
    # Very few predictions so far -- even with 2 of 3 being HIGH, there is
    # not enough evidence yet for a trustworthy statistic.
    window = ["HIGH", "HIGH", "LOW"]
    assert len(window) < DEFAULT_MIN_WINDOW_SIZE
    result = detect_spike(window, baseline_fraud_rate=BASELINE_RATE)
    assert result.insufficient_data is True
    assert result.is_spike is False
    assert result.anomaly_score == 0.0
    assert result.severity == "NONE"


def test_cold_start_empty_window_does_not_crash():
    result = detect_spike([], baseline_fraud_rate=BASELINE_RATE)
    assert result.insufficient_data is True
    assert result.is_spike is False
    assert result.window_size == 0
    assert result.current_fraud_rate == 0.0


def test_anomaly_score_responds_proportionally_not_just_binary():
    """A mild deviation must score strictly lower than a severe one -- the
    detector is a continuous statistic, not a trigger/no-trigger flag.
    """
    mild = detect_spike(_window(1, 50), baseline_fraud_rate=BASELINE_RATE)  # sub-threshold
    moderate = detect_spike(_window(2, 50), baseline_fraud_rate=BASELINE_RATE)  # spike, lower severity
    severe = detect_spike(_window(10, 50), baseline_fraud_rate=BASELINE_RATE)  # spike, higher severity

    assert mild.anomaly_score < moderate.anomaly_score < severe.anomaly_score
    assert mild.is_spike is False
    assert moderate.is_spike is True
    assert severe.is_spike is True
    # Severity actually differentiates across this range, not just the
    # raw score.
    assert moderate.severity != severe.severity


def test_default_window_size_is_50():
    assert DEFAULT_WINDOW_SIZE == 50


def test_below_baseline_rate_is_never_a_spike():
    # A window with a LOWER-than-baseline rate (here: none at all) must not
    # be flagged -- only an increase in fraud rate is anomalous.
    result = detect_spike(_window(0, 50), baseline_fraud_rate=0.05)
    assert result.is_spike is False
    assert result.anomaly_score == 0.0
