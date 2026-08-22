"""Seeds a HANDFUL of realistic SIMULATED chargebacks (and a couple of
refunds) against transactions already in the predictions table.

*** THIS IS FABRICATED DEMO DATA. *** There is no real chargeback history
anywhere in this project. The underlying transaction/prediction records
each seeded chargeback points at ARE real (replayed historical
transactions via simulator/simulate.py, or manual /predict calls) -- only
the fact that a "chargeback" happened against them is invented for this
demo. Never present the chargebacks/refunds themselves as real events;
always describe them as seeded/simulated in any UI-facing text.

Picks a deliberate mix so the demo can tell both honest stories:
  - chargebacks against HIGH-risk (HOLD) predictions: "we caught this in
    advance" -- the model already flagged it before the chargeback arrived.
  - chargebacks against LOW-risk (ALLOW) predictions: "this one slipped
    through" -- the model missed it, which is also worth showing honestly.

Usage:
    python src/evidence/seed_chargebacks.py [--reset]
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

import api.services.db as db_module  # noqa: E402
from api.services.db_models import ChargebackRecord, PredictionRecord, RefundRecord  # noqa: E402

HIGH_RISK_REASON = "unauthorized_transaction"
LOW_RISK_REASON = "fraudulent_card_use"
EXTRA_REASON = "product_not_received"


def seed(reset: bool = False) -> None:
    db_module.init_db()
    db = db_module.SessionLocal()
    try:
        if reset:
            deleted_cb = db.query(ChargebackRecord).delete()
            deleted_rf = db.query(RefundRecord).delete()
            db.commit()
            print(f"--reset: cleared {deleted_cb} existing chargebacks and {deleted_rf} existing refunds.")

        high_risk = (
            db.execute(
                select(PredictionRecord)
                .where(PredictionRecord.risk_tier == "HIGH")
                .order_by(PredictionRecord.timestamp)
            )
            .scalars()
            .all()
        )
        low_risk = (
            db.execute(
                select(PredictionRecord)
                .where(PredictionRecord.risk_tier == "LOW")
                .order_by(PredictionRecord.timestamp)
            )
            .scalars()
            .all()
        )

        if not high_risk or not low_risk:
            sys.exit(
                "Need at least one HIGH-risk and one LOW-risk prediction already stored to seed "
                "a realistic mix. Run simulator/simulate.py --spike first, then retry."
            )

        # ("we caught this") x3, ("this slipped through") x3, one more for
        # a round 7 -- a handful, per the brief, not a bulk dataset.
        picks: list[tuple[PredictionRecord, str, str]] = []
        for record in high_risk[:3]:
            picks.append((record, HIGH_RISK_REASON, "lost"))
        for record in low_risk[:3]:
            picks.append((record, LOW_RISK_REASON, "pending"))
        if len(low_risk) > 3:
            picks.append((low_risk[3], EXTRA_REASON, "won"))

        created_chargebacks = 0
        created_refunds = 0
        for i, (record, reason, cb_status) in enumerate(picks):
            existing = (
                db.query(ChargebackRecord).filter_by(transaction_id=record.transaction_id).first()
            )
            if existing is not None:
                continue  # don't double-seed the same transaction on a re-run

            # Roughly half of the "slipped through" cases also show a
            # refund attempt before the chargeback, for demo variety --
            # not every real chargeback is preceded by one.
            if reason == LOW_RISK_REASON and i % 2 == 0:
                refund = RefundRecord(
                    refund_id=f"rf_{uuid.uuid4().hex[:12]}",
                    transaction_id=record.transaction_id,
                    amount=record.amount,
                    timestamp=record.timestamp + timedelta(days=1),
                    reason="customer_dispute_pre_chargeback",
                )
                db.add(refund)
                created_refunds += 1

            chargeback = ChargebackRecord(
                chargeback_id=f"cb_{uuid.uuid4().hex[:12]}",
                transaction_id=record.transaction_id,
                reason=reason,
                amount=record.amount,
                timestamp=record.timestamp + timedelta(days=3, hours=i),
                status=cb_status,
            )
            db.add(chargeback)
            created_chargebacks += 1

        db.commit()
        print(f"Seeded {created_chargebacks} SIMULATED chargebacks and {created_refunds} SIMULATED refunds.")
        print(
            "Reminder: this is fabricated demo data layered onto real transaction/prediction "
            "records -- it is not real chargeback history."
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="Clear existing seeded chargebacks/refunds first")
    args = parser.parse_args()
    seed(reset=args.reset)
