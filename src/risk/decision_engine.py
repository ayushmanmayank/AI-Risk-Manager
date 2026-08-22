"""Map a scored transaction to a risk tier and an operational decision.

Risk tiers are driven by two configurable probability thresholds, not
hardcoded magic numbers:

    probability <  medium_threshold                -> LOW    -> ALLOW
    medium_threshold <= probability < high_threshold -> MEDIUM -> REVIEW
    probability >= high_threshold                    -> HIGH   -> HOLD
"""

from __future__ import annotations

from dataclasses import dataclass

from src.risk.expected_loss import DEFAULT_LOSS_RATE, expected_loss

DEFAULT_MEDIUM_THRESHOLD = 0.30
DEFAULT_HIGH_THRESHOLD = 0.70

RISK_TIER_TO_DECISION = {
    "LOW": "ALLOW",
    "MEDIUM": "REVIEW",
    "HIGH": "HOLD",
}


@dataclass(frozen=True)
class Decision:
    decision: str
    risk_tier: str
    threshold_used: float
    expected_loss: float
    reason_code: str


def decide(
    fraud_probability: float,
    transaction_amount: float,
    medium_threshold: float = DEFAULT_MEDIUM_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
    estimated_loss_rate: float = DEFAULT_LOSS_RATE,
) -> Decision:
    """Classify a transaction into a risk tier and return the full decision.

    Args:
        fraud_probability: Calibrated P(fraud) in [0, 1].
        transaction_amount: Transaction amount.
        medium_threshold: Probability at/above which a transaction is at
            least MEDIUM risk. Must be < high_threshold.
        high_threshold: Probability at/above which a transaction is HIGH risk.
        estimated_loss_rate: Passed through to expected_loss().

    Returns:
        Decision with the tier, the mapped action, the threshold boundary
        that determined the tier, the expected monetary loss, and a
        machine-readable reason code for audit/logging.
    """
    if not 0.0 <= medium_threshold <= 1.0 or not 0.0 <= high_threshold <= 1.0:
        raise ValueError("thresholds must be in [0, 1]")
    if medium_threshold >= high_threshold:
        raise ValueError(
            f"medium_threshold ({medium_threshold}) must be < high_threshold ({high_threshold})"
        )

    loss = expected_loss(fraud_probability, transaction_amount, estimated_loss_rate)

    if fraud_probability >= high_threshold:
        risk_tier = "HIGH"
        threshold_used = high_threshold
        reason_code = f"PROB_GE_HIGH_THRESHOLD({fraud_probability:.4f}>={high_threshold:.2f})"
    elif fraud_probability >= medium_threshold:
        risk_tier = "MEDIUM"
        threshold_used = medium_threshold
        reason_code = f"PROB_GE_MEDIUM_THRESHOLD({fraud_probability:.4f}>={medium_threshold:.2f})"
    else:
        risk_tier = "LOW"
        threshold_used = medium_threshold
        reason_code = f"PROB_LT_MEDIUM_THRESHOLD({fraud_probability:.4f}<{medium_threshold:.2f})"

    return Decision(
        decision=RISK_TIER_TO_DECISION[risk_tier],
        risk_tier=risk_tier,
        threshold_used=threshold_used,
        expected_loss=loss,
        reason_code=reason_code,
    )
