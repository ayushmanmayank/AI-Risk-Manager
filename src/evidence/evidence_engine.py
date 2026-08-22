"""Assembles a chargeback evidence package from already-fetched records.

Pure assembly logic only -- no DB access here (matches src/risk/*'s
pattern). See api/services/evidence_service.py for the DB lookups that
feed this.

THE LOOKUP CHAIN, as actually implemented in this system (be explicit
about what exists and what doesn't, per the Day 11 brief):

    chargeback -> transaction lookup -> customer lookup -> refund lookup
    -> risk_prediction lookup -> assembled timeline

- "transaction lookup" and "risk_prediction lookup" are THE SAME RECORD
  here: this system never built a separate transactions table --
  api/services/db_models.py:PredictionRecord is written once, at
  /predict time, and holds both the transaction's own fields (amount,
  time) and the model's risk assessment (fraud_probability, risk_tier,
  decision, SHAP explanation) together. There was nothing to gain by
  splitting one write into two tables that would only ever be read
  together, so this reports `transaction` and `risk_prediction` as two
  named fields in the response (matching the spec's chain) that both
  point at the same underlying data -- not two different sources
  quietly collapsed into one without saying so.
- "customer lookup" always returns CUSTOMER_NOT_AVAILABLE: this system
  has no customer data model at all (no signup, no account, no linkage
  from a transaction to a person). Rather than inventing a plausible-
  looking customer record, this is stated plainly every time.
- "refund lookup" is a real, separate table (api/services/db_models.py:
  RefundRecord) -- some chargebacks have a preceding refund, many don't,
  matching real-world variance.

Every value placed in the returned EvidencePackage comes directly from a
field on one of the three input records (chargeback, transaction, refund)
-- nothing here infers, estimates, or invents a fact that isn't already
in a database row.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

CUSTOMER_NOT_AVAILABLE = "not available -- this system has no customer data model"


@dataclass(frozen=True)
class TimelineEvent:
    event: str
    timestamp: datetime | None
    description: str


@dataclass(frozen=True)
class EvidenceSummary:
    was_flagged_in_advance: bool
    risk_tier_at_scoring: str | None
    decision_at_scoring: str | None
    fraud_probability_at_scoring: float | None
    narrative: str


@dataclass(frozen=True)
class EvidencePackage:
    chargeback_id: str
    transaction_id: str
    chargeback: dict
    transaction: dict | None
    customer: str
    refund: dict | None
    risk_prediction: dict | None
    timeline: list[TimelineEvent]
    summary: EvidenceSummary


def _min_timestamp_for_sort(timestamp: datetime | None) -> datetime:
    """Sort key helper: events with no real timestamp (the 'lookup failed'
    marker) sort first, never silently dropped from the timeline.
    """
    return timestamp if timestamp is not None else datetime.min.replace(tzinfo=timezone.utc)


def build_evidence_package(
    chargeback: dict,
    transaction: dict | None,
    refund: dict | None,
) -> EvidencePackage:
    """Build the full evidence package for one chargeback.

    Args:
        chargeback: {chargeback_id, transaction_id, reason, amount,
            timestamp, status} -- required, always present (the chargeback
            itself is what triggered this lookup).
        transaction: the PredictionRecord's fields as a dict (see
            api/services/evidence_service.py for the exact shape), or None
            if no prediction record exists for this transaction_id.
        refund: {refund_id, transaction_id, amount, timestamp, reason}, or
            None if no refund was ever filed for this transaction.
    """
    timeline: list[TimelineEvent] = []

    if transaction is not None:
        timeline.append(
            TimelineEvent(
                event="transaction_scored",
                timestamp=transaction["timestamp"],
                description=(
                    f"Transaction {chargeback['transaction_id']} (amount "
                    f"{transaction['amount']:.2f}) was scored by "
                    f"{transaction['model_version']}: fraud_probability="
                    f"{transaction['fraud_probability']:.4f}, risk_tier="
                    f"{transaction['risk_tier']}."
                ),
            )
        )
        timeline.append(
            TimelineEvent(
                event="decision_made",
                timestamp=transaction["timestamp"],
                description=f"Decision at scoring time: {transaction['decision']}.",
            )
        )
    else:
        timeline.append(
            TimelineEvent(
                event="transaction_lookup_failed",
                timestamp=None,
                description=(
                    f"No prediction record found for transaction_id "
                    f"'{chargeback['transaction_id']}'. No prior risk data available."
                ),
            )
        )

    if refund is not None:
        timeline.append(
            TimelineEvent(
                event="refund_issued",
                timestamp=refund["timestamp"],
                description=f"Refund of {refund['amount']:.2f} issued (reason: {refund['reason']}).",
            )
        )

    timeline.append(
        TimelineEvent(
            event="chargeback_filed",
            timestamp=chargeback["timestamp"],
            description=(
                f"Chargeback filed for {chargeback['amount']:.2f} "
                f"(reason: {chargeback['reason']}, status: {chargeback['status']})."
            ),
        )
    )

    timeline.sort(key=lambda e: _min_timestamp_for_sort(e.timestamp))

    if transaction is not None:
        was_flagged = transaction["decision"] != "ALLOW"
        risk_tier = transaction["risk_tier"]
        decision = transaction["decision"]
        fraud_probability = transaction["fraud_probability"]
        if was_flagged:
            narrative = (
                f"This transaction was already scored {risk_tier} risk and the system's "
                f"decision was {decision} BEFORE the chargeback was filed -- the model had "
                f"already identified this transaction as suspicious."
            )
        else:
            narrative = (
                f"This transaction was scored {risk_tier} risk and the system's decision was "
                f"{decision} -- the model did not flag it, and the fraud was not caught until "
                f"the chargeback arrived."
            )
    else:
        was_flagged = False
        risk_tier = None
        decision = None
        fraud_probability = None
        narrative = (
            "No prior risk prediction exists for this transaction_id -- cannot determine "
            "whether it was flagged in advance."
        )

    summary = EvidenceSummary(
        was_flagged_in_advance=was_flagged,
        risk_tier_at_scoring=risk_tier,
        decision_at_scoring=decision,
        fraud_probability_at_scoring=fraud_probability,
        narrative=narrative,
    )

    return EvidencePackage(
        chargeback_id=chargeback["chargeback_id"],
        transaction_id=chargeback["transaction_id"],
        chargeback=chargeback,
        transaction=transaction,
        customer=CUSTOMER_NOT_AVAILABLE,
        refund=refund,
        risk_prediction=transaction,  # same record as `transaction` -- see module docstring
        timeline=timeline,
        summary=summary,
    )
