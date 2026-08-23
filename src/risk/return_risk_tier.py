"""Map a return_probability to a simple risk tier for the return-risk
scorer (Tier 2).

No decision/expected-loss engine here (contrast: src/risk/decision_engine.py
for fraud) -- no return-handling cost model was defined for this feature,
only return_probability was asked for. These thresholds are round,
conventional choices re-picked for THIS model's own base rate (~35% in
the training data, versus the fraud model's ~0.17%) -- not the fraud
model's 0.30/0.70 copied over unexamined, which would be a mismatched,
weakly-justified choice for a completely different label distribution.
Like decision_engine.py's own thresholds, these are reasonable defaults,
not statistically derived from a labeled cost study (none exists for
returns here).
"""

from __future__ import annotations

LOW_MEDIUM_BOUNDARY = 0.30
MEDIUM_HIGH_BOUNDARY = 0.60


def risk_tier_for(return_probability: float) -> str:
    if return_probability >= MEDIUM_HIGH_BOUNDARY:
        return "HIGH"
    if return_probability >= LOW_MEDIUM_BOUNDARY:
        return "MEDIUM"
    return "LOW"
