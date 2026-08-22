# Demo script

A literal, rehearsable walkthrough. Target: **4-5 minutes**. Timings are
per-step targets, not hard stops — if you're mid-sentence when a timer
would end, finish the sentence, not the clock.

**Run this once before the room fills up, not during the demo** — and note
the two steps below can leave the Fraud Spike detector showing "active,"
which the last line fixes before you start:
```bash
docker compose up -d
python src/evidence/seed_chargebacks.py
```
If that second command exits with "Need at least one HIGH-risk and one
LOW-risk prediction already stored" (a genuinely fresh DB has neither
yet), it needs **both** — a spike burst alone only creates HIGH rows,
which still isn't enough (verified live: tried exactly that, it still
refused). Get some of each, then seed:
```bash
python simulator/simulate.py --count 5 --interval 0.1
python simulator/simulate.py --count 0 --spike --spike-size 10
python src/evidence/seed_chargebacks.py
```
**Either way, finish with this** — the spike burst above (or a leftover
one from a previous rehearsal) leaves the detector showing "active," and
you want the *first* spike the audience sees to be the one you trigger
live in step 6, not a stale one from setup:
```bash
python simulator/simulate.py --count 50 --interval 0.1
```
Open `/fraud-spike` and confirm it actually reads **"No active spike"**
(green) before the room fills up — don't assume it does. Leave the app
running via Docker at `http://localhost:3000` the whole time.

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
(green — see the pre-show setup above if it isn't). Leave that tab/window
visible, then in the terminal:
```bash
python simulator/simulate.py --count 0 --spike --spike-size 30
```
`--count 0` matters: without it, the command silently runs 12 "normal"
transactions first (simulate.py's default), adding ~30s of dead air
before the burst even starts.

**Read this before rehearsing more than once.** The burst always targets
the same fixed, deterministically-ranked highest-probability rows, and
content-hash dedup means any of them already sent this session (pre-show
setup, or an earlier rehearsal) come back as the *existing* row with its
*old* timestamp, which the rolling window won't count as recent. This is
**not a "use a bigger number" problem** — the entire test split has only
**40 rows** above the HIGH-risk threshold, period. There is no
`--spike-size` above that helps once they're all claimed; a full
rehearsal-heavy audit session confirmed this directly (`--spike-size 40`
consumed the entire pool; a following `--spike-size 30` then failed
completely). **The only reliable reset is a fresh database:**
```bash
docker compose down
rm data/predictions.db   # or: del data\predictions.db  on plain cmd.exe
docker compose up -d
```
then redo the pre-show setup above. Do this once, right before the actual
presentation, after you're done rehearsing — not between every rehearsal
(each reset also erases the seeded chargebacks and everything on the
Dashboard, so you'd redo more than just this step).

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
fixed, deterministically-ranked highest-probability rows; if they've
already been sent this session (including by `seed_chargebacks.py`'s
setup, or an earlier rehearsal of step 6), content-hash dedup returns the
existing row with its *old* timestamp, and the rolling window won't count
it as recent. This is not hypothetical — confirmed live during a
rehearsal-heavy audit: a second consecutive run at `--spike-size 10`
failed, and after enough further testing, **the entire 40-row pool of
HIGH-probability test rows was exhausted and `--spike-size 30` failed
completely too.** There is no larger number that fixes this once the pool
is used up — it's a hard ceiling (40 rows total ≥ the HIGH threshold in
the whole test split), not a "try bigger" problem. The only reliable fix
is a fresh database:
```bash
docker compose down
rm data/predictions.db
docker compose up -d
```
then redo the pre-show setup from the top. Don't reset between every
rehearsal (it also erases the seeded chargebacks) — reset once,
immediately before the real presentation, after rehearsing.

**Total meltdown — fall back to screenshots:** Day 10's cross-page
screenshot pass captured all 6 pages then-current; grab a fresh set the
morning of the demo the same way (open each page, screenshot) so they show
today's data, not stale numbers. Narrate from them exactly as written
above — the talking points don't depend on the live interaction actually
working, only on being able to point at *something* on screen.
