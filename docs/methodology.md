# Methodology notes

Short, honest notes on modeling decisions and known limitations. This is
not a fix-it list — it's a record of things worth knowing before trusting
a number from this project, written down instead of left as tribal
knowledge in a chat log.

## Known limitation: val/test boundary has a minor Time tie

The temporal split (`src/models/train_fraud_model.py`) divides
`data/processed/features.csv` by row index after sorting by `Time`, at
roughly 70% / 15% / 15% (train / validation / test). The train/validation
boundary is clean — no `Time` value appears on both sides of it.

The validation/test boundary is not perfectly clean. Three transactions
share the exact same `Time` value (151,328 seconds) at that boundary, and
the 85% index cut happens to fall between them: two land in validation,
one lands in test. Since `Time` only has 1-second resolution and multiple
transactions can occur within the same second, this kind of tie at a
boundary is expected, not a bug in the split logic itself.

**Practical impact.** `amount_zscore` (`src/features/build_features.py`)
is a rolling z-score computed over the prior 10,000 transactions in
`Time`-sorted order. Because of the tie above, the one test-set row at the
boundary has 2 of its 10,000 window entries drawn from validation-set
transactions rather than exclusively from train+earlier-test data. This is
**not** future-information leakage or label leakage — the window is still
strictly backward-looking by sort order, and no `Class` value is involved.
It is a small amount of cross-split feature contamination, confined to a
single row's `amount_zscore` value, diluted across a 10,000-row window.
Given the window size, the effect on that one feature value is negligible
and does not materially affect the test-set metrics reported elsewhere
(see the Day 5 audit notes for the actual TEST-set classification report).

This has not been fixed — fixing it properly means splitting on a
strictly-increasing tiebreak key (e.g. `Time` then original row order)
rather than a raw index cut, which is a one-line change but requires
retraining and re-evaluating the model, which is out of scope for a
same-day patch. Documented here so it's a known, accepted limitation
rather than a silent one.
