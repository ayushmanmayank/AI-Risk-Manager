"""Threshold-level operational cost accounting and threshold sweeps.

expected_cost = (false_positive_count * false_positive_cost)
              + (false_negative_count * false_negative_cost)

Default costs are placeholders, not calibrated business numbers:
  - false_positive_cost (default 5.0): cost of a manual review / customer
    friction from wrongly holding a legitimate transaction.
  - false_negative_cost (default 100.0): cost of letting a fraudulent
    transaction through undetected.
Both are simplifying flat constants for Day 2; a more accurate model would
make false_negative_cost proportional to the transaction amount (see
expected_loss.py) rather than a single flat number. Override both when
calling these functions with real cost estimates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_FALSE_POSITIVE_COST = 5.0
DEFAULT_FALSE_NEGATIVE_COST = 100.0
DEFAULT_SWEEP_THRESHOLDS = tuple(round(t, 2) for t in np.arange(0.1, 0.91, 0.1))


@dataclass(frozen=True)
class ThresholdCost:
    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int
    expected_cost: float


def confusion_counts_at_threshold(
    y_true: np.ndarray, y_prob: np.ndarray, threshold: float
) -> tuple[int, int, int, int]:
    """Return (tp, fp, fn, tn) for predictions thresholded at `threshold`."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= threshold).astype(int)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    return tp, fp, fn, tn


def expected_cost(
    false_positive_count: int,
    false_negative_count: int,
    false_positive_cost: float = DEFAULT_FALSE_POSITIVE_COST,
    false_negative_cost: float = DEFAULT_FALSE_NEGATIVE_COST,
) -> float:
    """Total operational cost implied by a confusion matrix's error counts."""
    if false_positive_count < 0 or false_negative_count < 0:
        raise ValueError("error counts must be >= 0")
    if false_positive_cost < 0 or false_negative_cost < 0:
        raise ValueError("costs must be >= 0")
    return (
        false_positive_count * false_positive_cost
        + false_negative_count * false_negative_cost
    )


def sweep_thresholds(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    thresholds: tuple[float, ...] = DEFAULT_SWEEP_THRESHOLDS,
    false_positive_cost: float = DEFAULT_FALSE_POSITIVE_COST,
    false_negative_cost: float = DEFAULT_FALSE_NEGATIVE_COST,
) -> list[ThresholdCost]:
    """Compute expected_cost at each threshold in `thresholds`.

    Returns results sorted by threshold ascending, one row per threshold.
    """
    results = []
    for threshold in thresholds:
        tp, fp, fn, tn = confusion_counts_at_threshold(y_true, y_prob, threshold)
        cost = expected_cost(fp, fn, false_positive_cost, false_negative_cost)
        results.append(
            ThresholdCost(threshold=float(threshold), tp=tp, fp=fp, fn=fn, tn=tn, expected_cost=cost)
        )
    return sorted(results, key=lambda r: r.threshold)


def best_threshold(results: list[ThresholdCost]) -> ThresholdCost:
    """Return the ThresholdCost with the lowest expected_cost."""
    if not results:
        raise ValueError("results is empty")
    return min(results, key=lambda r: r.expected_cost)


def is_monotonic_ish(results: list[ThresholdCost]) -> bool:
    """Heuristic check: cost forms a single valley (decreases then increases).

    Real cost curves from a threshold sweep are rarely perfectly monotonic
    on either side (integer count jumps cause local ties/bumps), so this
    checks for at most one direction change from non-increasing to
    non-decreasing, rather than requiring strict monotonicity.
    """
    costs = [r.expected_cost for r in sorted(results, key=lambda r: r.threshold)]
    direction_changes = 0
    previous_direction = 0
    for earlier, later in zip(costs, costs[1:]):
        if later > earlier:
            direction = 1
        elif later < earlier:
            direction = -1
        else:
            direction = previous_direction
        if previous_direction == 1 and direction == -1:
            direction_changes += 1
        previous_direction = direction or previous_direction
    return direction_changes <= 1
