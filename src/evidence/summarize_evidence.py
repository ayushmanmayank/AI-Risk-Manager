"""Builds a short, readable narrative summary of a chargeback's evidence
package using pure Python string templates -- no external API call, no
LLM, no network dependency, no API key.

WHY TEMPLATES, NOT AN LLM: an earlier version of this module called the
Anthropic API to generate this text. That was dropped before shipping --
this environment has no ANTHROPIC_API_KEY available, and building a
feature that's permanently dark without one isn't worth shipping. This
version produces the same *kind* of readable narrative directly from the
already-assembled EvidencePackage's own fields, using conditional string
formatting only. Every clause in the output traces to a literal field on
the package (see build_facts below for the exact mapping) -- there is no
summarization judgment call being made, no paraphrasing, and nothing to
hallucinate, because nothing here is produced by anything other than
fixed Python logic operating on data that was already verified and
traceable before this module ever runs (see
src/evidence/evidence_engine.py's own docstring on that guarantee).

No caching story is needed here either (contrast: an LLM call would cost
money and add latency per request, which is what would have justified
caching in the dropped version). This is cheap enough to recompute on
every request, exactly like evidence_engine.EvidenceSummary.narrative
already is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.evidence.evidence_engine import EvidencePackage

# How many of the top SHAP-ranked features get named in the "primarily
# due to ..." clause. Matches Transaction Detail's own "top risk factors"
# convention (Day 4) of showing a small, digestible handful, not the
# whole ranked list.
TOP_FEATURES_PER_CLAUSE = 2


@dataclass(frozen=True)
class SummaryResult:
    text: str | None
    available: bool
    error: str | None


def _lowercase_first(text: str) -> str:
    return text[0].lower() + text[1:] if text else text


def _format_probability_pct(probability: float) -> str:
    return f"{probability * 100:.1f}%"


def _format_date(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%d")


def _describe_timing(transaction_timestamp: datetime, chargeback_timestamp: datetime) -> str:
    delta_days = (chargeback_timestamp - transaction_timestamp).days
    if delta_days > 1:
        return f"{delta_days} days before the chargeback was filed"
    if delta_days == 1:
        return "1 day before the chargeback was filed"
    if delta_days == 0:
        return "less than a day before the chargeback was filed"
    # Scored after the chargeback itself -- an unusual but real state
    # (e.g. a backfilled/late prediction record); state it plainly rather
    # than forcing it into the normal "before" phrasing.
    return f"{abs(delta_days)} days after the chargeback was filed"


def _feature_phrase(features: list[dict]) -> str | None:
    """Joins the top features' own labels, already-honest strings sourced
    from src/models/explain.py:label_for() -- e.g. "Hour of day" or
    "Anonymized signal V14". Never invents a meaning for an anonymized
    signal; only ever repeats the label verbatim (case-adjusted for
    mid-sentence placement).
    """
    if not features:
        return None
    labels = [_lowercase_first(feature["label"]) for feature in features[:TOP_FEATURES_PER_CLAUSE]]
    return labels[0] if len(labels) == 1 else " and ".join(labels)


def _refund_clause(refund: dict | None) -> str:
    if refund is None:
        return "No refund was issued prior to the dispute."
    return (
        f"A refund of ${refund['amount']:.2f} was issued on "
        f"{_format_date(refund['timestamp'])} prior to the dispute."
    )


def generate_summary(package: EvidencePackage) -> SummaryResult:
    """Builds the narrative. Every value used below reads directly off
    `package` (chargeback/transaction/refund dicts, the EvidenceSummary,
    or the SHAP feature lists already stored on the transaction) --
    nothing is looked up, inferred, or computed from any other source.

    Wrapped in a broad except as a defensive measure only: there is no
    genuine external failure mode left (no network call, no API key), but
    an unexpected shape in `package` should still degrade to
    available=False rather than break the evidence page, matching this
    feature's original design contract.
    """
    try:
        summary = package.summary
        refund_clause = _refund_clause(package.refund)

        if package.transaction is None:
            text = (
                "No prior risk prediction exists for this transaction_id, so it isn't possible to "
                f"say whether it was flagged in advance. {refund_clause}"
            )
            return SummaryResult(text=text, available=True, error=None)

        transaction = package.transaction
        risk_tier = summary.risk_tier_at_scoring
        probability_pct = _format_probability_pct(summary.fraud_probability_at_scoring)
        timing = _describe_timing(transaction["timestamp"], package.chargeback["timestamp"])

        if summary.was_flagged_in_advance:
            toward_phrase = _feature_phrase(transaction["shap_explanation"]["top_positive_features"])
            reason_clause = f", primarily due to {toward_phrase}" if toward_phrase else ""
            text = (
                f"This transaction was flagged {risk_tier} risk ({probability_pct} fraud probability) "
                f"{timing}{reason_clause}. {refund_clause}"
            )
        else:
            away_phrase = _feature_phrase(transaction["shap_explanation"]["top_negative_features"])
            reason_clause = f", largely due to {away_phrase}" if away_phrase else ""
            text = (
                f"This transaction was scored {risk_tier} risk ({probability_pct} fraud probability) and "
                f"allowed through{reason_clause} -- the model did not flag it, and the fraud was not caught "
                f"until the chargeback arrived. {refund_clause}"
            )

        return SummaryResult(text=text, available=True, error=None)
    except Exception as exc:  # noqa: BLE001 -- see docstring: must never break the evidence page
        return SummaryResult(text=None, available=False, error=f"Unexpected error building summary: {exc}")
