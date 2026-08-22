"""Root conftest so `src` is importable as a package during test collection.

Presence of this file at the repo root makes pytest add the repo root to
sys.path (prepend import mode), which lets test modules do
`from src.risk.decision_engine import decide` etc.
"""
