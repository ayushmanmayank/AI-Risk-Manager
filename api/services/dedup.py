"""Content-hash fallback for detecting duplicate /predict submissions that
arrive without a client-supplied transaction_id (see api/routes/predict.py).

Scope, deliberately narrow: this only kicks in when the client did NOT
supply a transaction_id. If a client supplies an explicit, non-colliding
transaction_id, that request always creates its own row -- an explicit id
is the client telling us this is a distinct event, and that takes
precedence over content matching.
"""

from __future__ import annotations

import hashlib
import json

RAW_FEATURE_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]


def compute_content_hash(payload: dict) -> str:
    """Deterministic hash of a transaction's raw feature values only.

    Excludes transaction_id and any server-assigned field (timestamp,
    fraud_probability, ...) by construction -- it only ever reads
    RAW_FEATURE_COLUMNS from `payload`. Two calls with the same real-world
    transaction content hash identically regardless of dict key order or
    which float repr the caller used, because values are normalized to
    Python float before serializing.
    """
    canonical = {key: float(payload[key]) for key in RAW_FEATURE_COLUMNS}
    serialized = json.dumps(canonical, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
