"""Tests for the Day 2 expected-loss and decision engine modules."""

from __future__ import annotations

import numpy as np
import pytest

from src.risk.cost_engine import (
    DEFAULT_SWEEP_THRESHOLDS,
    confusion_counts_at_threshold,
    expected_cost,
    is_monotonic_ish,
    sweep_thresholds,
)
from src.risk.decision_engine import decide
from src.risk.expected_loss import expected_loss


def test_low_risk_transaction_returns_allow():
    result = decide(fraud_probability=0.05, transaction_amount=100.0)
    assert result.risk_tier == "LOW"
    assert result.decision == "ALLOW"


def test_high_risk_transaction_returns_hold():
    result = decide(fraud_probability=0.95, transaction_amount=500.0)
    assert result.risk_tier == "HIGH"
    assert result.decision == "HOLD"


def test_medium_risk_transaction_returns_review():
    result = decide(fraud_probability=0.50, transaction_amount=200.0)
    assert result.risk_tier == "MEDIUM"
    assert result.decision == "REVIEW"


def test_decide_respects_custom_thresholds():
    # probability 0.4 is HIGH only if high_threshold is lowered below it.
    result = decide(
        fraud_probability=0.40,
        transaction_amount=100.0,
        medium_threshold=0.10,
        high_threshold=0.30,
    )
    assert result.risk_tier == "HIGH"
    assert result.decision == "HOLD"
    assert result.threshold_used == 0.30


def test_expected_loss_matches_manual_math():
    # 0.8 probability * 250.0 amount * 1.0 loss rate = 200.0
    assert expected_loss(0.8, 250.0, estimated_loss_rate=1.0) == pytest.approx(200.0)
    # partial loss rate: 0.5 * 400.0 * 0.6 = 120.0
    assert expected_loss(0.5, 400.0, estimated_loss_rate=0.6) == pytest.approx(120.0)


def test_expected_loss_rejects_invalid_probability():
    with pytest.raises(ValueError):
        expected_loss(1.5, 100.0)


def test_decision_expected_loss_field_matches_expected_loss_function():
    result = decide(fraud_probability=0.9, transaction_amount=300.0, estimated_loss_rate=1.0)
    assert result.expected_loss == pytest.approx(expected_loss(0.9, 300.0, 1.0))


def test_confusion_counts_at_threshold():
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_prob = np.array([0.9, 0.4, 0.6, 0.1, 0.2, 0.05])
    # threshold 0.5 -> predicted positive: indices 0 (0.9), 2 (0.6)
    tp, fp, fn, tn = confusion_counts_at_threshold(y_true, y_prob, 0.5)
    assert (tp, fp, fn, tn) == (1, 1, 2, 2)


def test_expected_cost_matches_manual_math():
    # 2 false positives * 5.0 + 3 false negatives * 100.0 = 310.0
    assert expected_cost(2, 3, false_positive_cost=5.0, false_negative_cost=100.0) == pytest.approx(310.0)


def test_threshold_sweep_returns_monotonic_ish_cost_curve():
    rng = np.random.default_rng(42)
    n = 2000
    y_true = (rng.random(n) < 0.05).astype(int)
    # Give positives higher scores on average so there is a real signal,
    # producing a sensible single-valley cost curve.
    y_prob = np.where(
        y_true == 1,
        np.clip(rng.normal(0.7, 0.2, n), 0, 1),
        np.clip(rng.normal(0.2, 0.15, n), 0, 1),
    )

    results = sweep_thresholds(y_true, y_prob)
    assert len(results) == len(DEFAULT_SWEEP_THRESHOLDS)
    assert is_monotonic_ish(results), (
        "Cost curve has more than one valley; check sweep_thresholds/is_monotonic_ish "
        f"on this input: {[(r.threshold, r.expected_cost) for r in results]}"
    )
