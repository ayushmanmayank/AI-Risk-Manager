"""Expected-loss calculation for a single scored transaction.

Simplifying assumption (Day 2): ``estimated_loss_rate`` defaults to 1.0,
i.e. we assume the *full* transaction amount is lost on a fraudulent
transaction that is not caught. In reality only a fraction of a fraud's
amount is typically unrecoverable (partial chargebacks, recovered goods,
insurance, etc.), so this is a conservative upper bound, not a calibrated
loss model. Revisit once real chargeback/recovery data is available.
"""

from __future__ import annotations

DEFAULT_LOSS_RATE = 1.0


def expected_loss(
    fraud_probability: float,
    transaction_amount: float,
    estimated_loss_rate: float = DEFAULT_LOSS_RATE,
) -> float:
    """Return the expected monetary loss for one transaction.

    expected_loss = fraud_probability * transaction_amount * estimated_loss_rate

    Args:
        fraud_probability: Calibrated P(fraud) in [0, 1].
        transaction_amount: Transaction amount (same currency units throughout).
        estimated_loss_rate: Fraction of the amount assumed unrecoverable if
            the transaction is fraudulent. Defaults to 1.0 (full amount at risk).

    Raises:
        ValueError: If fraud_probability is outside [0, 1], or amount/loss
            rate are negative.
    """
    if not 0.0 <= fraud_probability <= 1.0:
        raise ValueError(f"fraud_probability must be in [0, 1], got {fraud_probability}")
    if transaction_amount < 0:
        raise ValueError(f"transaction_amount must be >= 0, got {transaction_amount}")
    if estimated_loss_rate < 0:
        raise ValueError(f"estimated_loss_rate must be >= 0, got {estimated_loss_rate}")

    return fraud_probability * transaction_amount * estimated_loss_rate
