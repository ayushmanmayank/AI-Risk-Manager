# Demo script

A literal, rehearsable walkthrough. Target: **4-5 minutes**. Timings are
per-step targets, not hard stops — if you're mid-sentence when a timer
would end, finish the sentence, not the clock.

**Run this once before the room fills up, not during the demo:**
```bash
docker compose up -d
python src/evidence/seed_chargebacks.py   # no-ops harmlessly if already seeded
```
Leave the app running via Docker at `http://localhost:3000` the whole time.
Don't run `--spike` as a warm-up — you want the *first* spike the audience
sees to be the one you trigger live in step 6.

---

## 1. Open with the problem framing — ~20s

**Say:** "Most fraud tools just say 'this is fraud' or 'this isn't.' That's
not actually a decision — it doesn't tell you how much is at stake or what
to do about it. This system scores a transaction's risk, turns that into
an expected dollar loss, and only then makes a cost-aware call: allow,
review, or hold. And it explains itself at every step."

**Do:** nothing yet — this is spoken over a blank screen or the browser
about to open. Don't open the Dashboard until you say "score."

---

## 2. Dashboard — ~15s

**Do:** open `http://localhost:3000/` (already loaded in a tab, ideally).

**Say:** "This is everything scored so far this session — real predictions
from a real trained model, not mock numbers. Risk tier breakdown, decision
breakdown, average expected loss." Point at the bar chart, move on fast —
this page is context, not the payoff.

---

## 3. Generate live traffic — ~30s

**Do:** in a visible terminal:
```bash
python simulator/simulate.py --count 10
```

**Say (while it runs):** "This is replaying real transactions from the
model's held-out test split — data it never saw during training — through
the actual `/predict` endpoint, live, right now. Not synthetic data." When
it finishes, flip back to the Dashboard tab and refresh: "And the numbers
just moved."

---

## 4. High-Risk Transactions → Transaction Detail (SHAP) — ~45s

**Do:** click **High-Risk Transactions** in the nav → click any `HIGH` row.

**Say:** "Every prediction ships with an explanation, not just a score."
Point at **Top risk factors**: "These are the signals that pushed this
toward fraud — most of the predictive power here is in the dataset's
anonymized PCA components, so I label those honestly as anonymized signals
rather than inventing a fake meaning for them." Point at one readable
feature if present (e.g. `amount_zscore`): "This one we *can* read — it's
saying this amount is unusual relative to recent spending pattern."

---

## 5. Threshold Simulator — the differentiator — ~60s

**Do:** click **Threshold Simulator**. Drag the slider slowly from low
(~0.1) to high (~0.9) and back to somewhere in the middle.

**Say:** "This is the core tradeoff the whole system is built around, made
concrete. Drag the threshold down" *(drag left)* "— recall goes up, we
catch more fraud, but precision drops, meaning more legitimate customers
get flagged. Drag it up" *(drag right)* "— less customer friction, but we
miss more fraud. There's no setting that improves both. And this isn't
re-running the model on every drag — it's re-thresholding pre-computed
validation-set probabilities, which is why it's instant." Let the chart's
dashed line visibly track the slider at least twice before moving on —
this is the moment to slow down, not rush.

---

## 6. Fraud Spike — live detection — ~40s

**Do:** click **Fraud Spike** first — it should read **No active spike**
(green). Leave that tab/window visible, then in the terminal:
```bash
python simulator/simulate.py --spike --spike-size 10
```

**Say (while it runs):** "This is bursting real high-probability
transactions from the test set — again, genuinely held-out data, not
fabricated. Watch the page — I'm not touching it." Within a few seconds
(it polls every 3s) the banner flips to red/active with a severity and an
anomaly score. "That's a live statistical test — the model's own predicted
fraud rate on this traffic against its training baseline — not a hardcoded
rule."

---

## 7. Chargeback Center — one caught, one missed — ~45s

**Do:** click **Chargebacks**. Click a row badged **Flagged in advance**.

**Say:** "This chargeback data is seeded for the demo — labeled as such
everywhere, including on this page — because there's no real chargeback
history to work with. But the transaction and risk data underneath is
real." Point at the green banner: "Here, the model already held this
transaction *before* the dispute ever came in."

**Do:** back out, click a row badged **Not flagged**.

**Say:** "And here's the honest other case — the model scored this LOW and
let it through, and it turned out to be a chargeback anyway. I'd rather
show that than pretend the model catches everything."

---

## 8. Model Performance — close on the real numbers — ~25s

**Do:** click **Model Performance**.

**Say:** "Last thing, and the one number set in this whole demo that isn't
live traffic: precision 88%, recall 73%, on a **held-out test set** —
15% of the data the model never touched during training, tuning, or
threshold selection. Touched exactly once, at the end." Point at the
confusion matrix briefly.

---

## 9. Closing line — ~10s

**Say, verbatim or close to it:** "So — real fraud model, real dataset,
real audited metrics. Live traffic on the other pages is genuine
historical data replayed for the demo, not fabricated. Chargebacks are
seeded, labeled as such. And return/chargeback *prediction* is explicitly
out of scope — there's no labeled data to train that against, and I'd
rather say that than fake a model for it."

---

## If something breaks live

**Container not responding:**
```bash
docker compose ps          # check both show "Up" / backend "healthy"
docker compose logs backend --tail 50
docker compose restart backend
```
If a rebuild is truly needed, `docker compose up --build -d` — but this
takes a couple of minutes, too long mid-demo. Fall back to screenshots
(below) and narrate over them instead of stalling.

**Frontend loads but shows no data / a network error banner:** almost
always the backend container. Check `docker compose ps` first, not the
frontend.

**`--spike` doesn't visibly trigger:** the burst always targets the same
handful of highest-probability rows; if they've already been sent this
session (including by `seed_chargebacks.py`, which claims 3 of them),
content-hash dedup returns the existing row with its *old* timestamp, and
the rolling window won't count it as recent. Re-run with a larger
`--spike-size` (15-20) — there are dozens of test rows at effectively the
same ~86% probability, so this always has headroom. This is a known,
understood behavior (see README § Known Limitations), not a bug to debug
live.

**Total meltdown — fall back to screenshots:** Day 10's cross-page
screenshot pass captured all 6 pages then-current; grab a fresh set the
morning of the demo the same way (open each page, screenshot) so they show
today's data, not stale numbers. Narrate from them exactly as written
above — the talking points don't depend on the live interaction actually
working, only on being able to point at *something* on screen.
