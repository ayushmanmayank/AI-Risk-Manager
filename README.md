# AI Risk Manager — Merchant Fraud Detection

An AI-powered risk management system for merchant fraud detection: it scores
each transaction for fraud risk, translates that risk into an expected
monetary loss, turns that into an operational decision (allow / review /
hold), and explains *why* — every prediction ships with a SHAP-based
breakdown of which signals pushed it toward or away from fraud. On top of
that core loop sit two purpose-built responders: a rolling fraud-rate
**spike detector** that flags anomalous bursts of high-risk traffic in real
time, and a **chargeback evidence responder** that assembles a chronological,
fact-only evidence package (was this transaction already flagged before the
chargeback arrived, or did it slip through?) for any disputed transaction.

Built over a 13-day solo sprint. Every number quoted anywhere in this
project traces to a real computation against a real dataset — no metric is
hand-picked or fabricated, and every place demo/simulated data is used
instead of a real, audited result is labeled as such in the UI and in this
document.

## Table of contents

1. [Problem statement alignment](#problem-statement-alignment)
2. [Installation](#installation)
3. [Environment variables](#environment-variables)
4. [Dataset setup](#dataset-setup)
5. [Model training](#model-training-optional--reproducing-from-scratch)
6. [Running the app](#running-the-app)
7. [Demo walkthrough](#demo-walkthrough)
8. [API endpoint reference](#api-endpoint-reference)
9. [Model performance (real, audited test-set numbers)](#model-performance-real-audited-test-set-numbers)
10. [Known limitations](#known-limitations-stated-honestly)
11. [Tech stack](#tech-stack)

## Problem statement alignment

This project directly addresses three things named in the hackathon brief:

- **The core fraud detector.** An XGBoost classifier, Platt-calibrated, with
  measured precision/recall reported on a genuinely held-out **test** split
  (not validation — see [§9](#model-performance-real-audited-test-set-numbers)),
  a configurable-threshold decision engine, and per-prediction SHAP
  explanations.
- **"Fraud-spike detector"** — `src/anomaly/spike_detector.py` +
  `GET /api/v1/alerts` + the **Fraud Spike** dashboard page: a rolling
  fraud-rate anomaly detector (z-test against a training-derived baseline)
  that raises and persists an alert when recent traffic's HIGH-risk rate
  deviates significantly from normal.
- **"Chargeback evidence responder"** — `src/evidence/evidence_engine.py` +
  `GET /api/v1/chargebacks` + the **Chargeback Center** page: given a
  chargeback, assembles a fact-only timeline (transaction scored → decision
  made → refund if any → chargeback filed) and states plainly whether the
  system had already flagged the transaction *before* the chargeback
  arrived — the "we told you so" vs. "this one slipped through" distinction,
  both reported honestly.

## Installation

First, clone the repo and `cd` into it — every command below assumes you're
running from the project root unless stated otherwise:

```bash
git clone https://github.com/ayushmanmayank/razorpay-track-2-.git
cd razorpay-track-2-
```

### Option A: Docker (recommended)

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (bundled
  with modern Docker Desktop; `docker compose version` should print
  something).

### Option B: Manual (no Docker)

- Python 3.11+ (developed against 3.12/3.14; no version-specific syntax used).
  A virtual environment is recommended but not required:
  `python -m venv .venv && source .venv/bin/activate` (or
  `.venv\Scripts\activate` on Windows) before the `pip install` below.
- Node.js 20.19+ or 22.12+ (Vite's own minimum — see `frontend/package.json`)
- `pip install -r requirements.txt` from the project root
- `npm install` inside `frontend/`

Both options still need the dataset step below — **that's not optional
either way**, and it's the single most common place a first run will fail
if skipped.

> **Docker status:** `docker compose up --build` has been run and verified
> end-to-end from a clean state (both containers healthy, frontend calling
> backend across published ports with no CORS errors, a real `/predict`
> call returning a real SHAP explanation, and SQLite data confirmed to
> survive a `docker compose down` / `up` cycle). If it still doesn't come up
> cleanly on your machine, the manual (Option B) path is fully equivalent
> and has been run and verified directly, repeatedly, throughout
> development.

## Environment variables

Copy `.env.example` to `.env` (optional — every value has a working default
baked into `docker-compose.yml`):

```bash
cp .env.example .env
```

| Variable | Default | What it's for |
|---|---|---|
| `BACKEND_PORT` | `8000` | Host port the API is published on |
| `FRONTEND_PORT` | `3000` | Host port the web app is published on |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000` | Comma-separated origins the backend accepts cross-origin requests from |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Baked into the frontend build; where the browser sends API calls |

Two things worth understanding, not just copying:

- `VITE_API_BASE_URL` is compiled into the frontend's static JS at **build**
  time (Vite env vars aren't read at container runtime), so changing it
  requires rebuilding the frontend image/bundle, not just restarting a
  container.
- Both `VITE_API_BASE_URL` and every entry in `CORS_ORIGINS` must be URLs
  your **browser** can reach — `localhost` + a *published* port — never a
  Docker-internal service name like `http://backend:8000`. The browser runs
  on your host machine, not inside the Compose network; a container-only
  hostname would never appear in a real request's `Origin` header, and CORS
  would silently fail. This is the most common way this kind of setup
  breaks.

## Dataset setup

The dataset (Kaggle's [`mlg-ulb/creditcardfraud`](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud),
284,807 transactions, 492 fraud, ~0.172% positive class) is not — and
cannot be — committed to this repo: it requires a free Kaggle account to
download, and at 150MB+ it has no business living in git history anyway.

1. Create a free Kaggle account if you don't have one, and download
   `creditcard.csv` from
   [kaggle.com/datasets/mlg-ulb/creditcardfraud](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud).
2. Place it at `data/raw/creditcard.csv` (the exact filename matters).
3. Build the engineered feature set (adds `amount_log`, `hour_of_day`,
   `amount_zscore` on top of the raw `Time`/`Amount`/`V1`-`V28`/`Class`
   columns — see `src/features/build_features.py` for exactly what each one
   is and how it's computed causally, with no future-data leakage):

   ```bash
   python src/features/build_features.py
   ```

   This writes `data/processed/features.csv` (~160MB, also gitignored —
   fully regenerable, so it's never committed either). **This step is
   required before the API will start** — `data/processed/features.csv` is
   read at startup by four different services (the model loader, the
   anomaly detector's baseline, the threshold simulator, and the model-info
   endpoint), all of which will fail to start without it.

## Model training (optional — reproducing from scratch)

A trained model (`models/fraud_model_v1.pkl`, ~600KB) is already committed
to this repo, so **you do not need to retrain to run the demo**. If you want
to reproduce it from scratch anyway:

```bash
python src/models/train_fraud_model.py
```

This does a **temporal** split (70% train / 15% validation / 15% test, in
chronological order by `Time` — never a random shuffle, since a fraud model
evaluated on shuffled data would leak future information into training),
trains an XGBoost classifier with `scale_pos_weight` set for the ~0.17%
class imbalance, Platt-calibrates its output probabilities, and evaluates
**only on validation** — the test split is never touched during training,
tuning, or threshold selection. It's used exactly once, at the very end, for
the final audited numbers in [§9](#model-performance-real-audited-test-set-numbers).

Output: an updated `models/fraud_model_v1.pkl`, plus validation metrics
printed to the console.

## Running the app

> Make sure you've completed [Dataset setup](#dataset-setup) first — both
> options below will start, but the backend will fail immediately without
> `data/processed/features.csv` already in place.

### Docker

From the project root (where `docker-compose.yml` lives):

```bash
docker compose up --build
```

- API: `http://localhost:8000` (docs at `http://localhost:8000/docs`)
- Web app: `http://localhost:3000`

Stop with `docker compose down` (add `-v` to also remove the named volume
state, though this project uses a bind mount for `data/`, so your SQLite DB
and features file live on your host regardless and aren't affected by `-v`).

### Manual (no Docker)

Two terminals, from the project root:

```bash
# Terminal 1 — backend
python -m uvicorn api.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

- API: `http://localhost:8000`
- Web app: `http://localhost:5173` (Vite's default dev port)

## Demo walkthrough

A suggested tour, roughly in the order a judge would want to see the story:

1. **Dashboard** (`/`) — total transactions scored so far, risk-tier
   distribution, decision breakdown. Empty at first; that's expected and
   handled explicitly (a calm "no predictions yet" state, not a blank
   screen) — populate it with step 2.

2. **Generate live traffic.** In a separate terminal:

   ```bash
   python simulator/simulate.py --count 12
   ```

   This replays 12 **real, held-out test-split transactions** (never seen
   during training or evaluation) through `POST /predict`, at a
   human-watchable pace, printing each result (risk tier, decision, fraud
   probability) to the console for narration. Refresh the Dashboard —
   real numbers now.

3. **High-Risk Transactions** (`/high-risk`) → click any row → **Transaction
   Detail** — the full SHAP breakdown for that one prediction: which
   anonymized signals (`V1`-`V28`) or readable features (`amount_zscore`,
   `hour_of_day`) pushed it toward or away from fraud.

4. **Fraud Spike** (`/fraud-spike`) — should read "No active spike" (green).
   Now run:

   ```bash
   python simulator/simulate.py --count 0 --spike --spike-size 30
   ```

   Leave the Fraud Spike page open while this runs — it auto-polls every 3s
   and will flip to an active-spike banner (severity-colored, with an
   anomaly z-score and a persisted alert-history entry) **without a manual
   refresh**. `--count 0` skips `simulate.py`'s default 12-transaction
   normal warmup (dead air you don't want mid-demo). On a **fresh
   database** this reliably triggers. On a **repeatedly rehearsed** one it
   can stop working entirely, with no `--spike-size` that fixes it — see
   Known Limitations below, this is a hard ceiling, not a "use a bigger
   number" problem.

5. **Threshold Simulator** (`/threshold-simulator`) — drag the slider and
   watch precision/recall/expected-loss update in real time (sub-20ms
   round trip; it's re-thresholding pre-computed validation-set
   probabilities, not re-scoring anything). This page *is* the demo of the
   central tradeoff: lower threshold catches more fraud but flags more
   legitimate transactions; higher threshold does the reverse.

6. **Model Performance** (`/model-performance`) — the real, audited
   held-out **test**-set numbers (not validation, not demo traffic — see
   the page's own explicit labeling and [§9](#model-performance-real-audited-test-set-numbers)).

7. **Chargeback Center** (`/chargebacks`) — seed a handful of realistic,
   clearly-labeled **simulated** chargebacks against the real predictions
   already scored:

   ```bash
   python src/evidence/seed_chargebacks.py
   ```

   Click into a "Flagged in advance" case (the model already held it before
   the chargeback), then a "Not flagged" case (the honest missed-fraud
   story) — both evidence timelines are assembled entirely from real
   database records, with any genuinely unavailable field (there is no
   customer data model in this system) stated as "not available," never
   invented.

## API endpoint reference

All endpoints are prefixed `/api/v1`. Interactive docs (Swagger UI) are
available at `/docs` on the running backend.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Confirms the model is loaded and the DB is reachable |
| `POST` | `/predict` | Scores one transaction: fraud probability, risk tier, decision, expected loss, SHAP explanation. Content-hash deduped if no `transaction_id` is supplied. |
| `GET` | `/transactions` | Paginated list of predictions made so far |
| `GET` | `/transactions/{transaction_id}` | Full detail (incl. SHAP) for one prediction |
| `GET` | `/analytics` | Aggregate stats: totals, risk-tier/decision breakdowns, average expected loss |
| `GET` | `/alerts` | Live fraud-spike status + persisted alert history |
| `POST` | `/simulate` | Re-thresholds the precomputed validation set at any threshold — precision, recall, FPR, expected cost |
| `GET` | `/models` | Model metadata + real held-out test-set metrics |
| `GET` | `/chargebacks` | List of (seeded/simulated) chargebacks with risk score at time of transaction |
| `GET` | `/chargebacks/{chargeback_id}` | Full assembled evidence package for one chargeback |

## Model performance (real, audited test-set numbers)

These are the actual numbers from scoring the model against the **test**
split — the 15% of the dataset held out from training, validation, *and*
threshold selection, touched exactly once. Reproducible any time via
`GET /api/v1/models`, which recomputes these from the model file and
`features.csv` at every startup rather than hardcoding them, specifically
so this table can never silently drift from what the pipeline actually
produces.

| Metric | Value |
|---|---|
| Precision | 0.8837 (88.37%) |
| Recall | 0.7308 (73.08%) |
| F1 | 0.8000 |
| PR-AUC | 0.7602 |
| ROC-AUC | 0.9615 |
| False positive rate | 0.0117% (5 / 42,670 legitimate) |
| False negative rate | 26.92% (14 / 52 actual fraud) |

Confusion matrix (threshold = 0.50, 42,722 test transactions):

| | Predicted legit | Predicted fraud |
|---|---|---|
| **Actual legit** | 42,665 (TN) | 5 (FP) |
| **Actual fraud** | 14 (FN) | 38 (TP) |

**On "real" vs. "simulated" data, stated plainly:** the numbers above are
the one genuine, audited measurement of model quality in this project. The
**Dashboard**, **High-Risk Transactions**, and **Fraud Spike** pages instead
show predictions made *during a demo session* — either real historical
transactions replayed by `simulator/simulate.py` (never fabricated; they're
genuine rows from the dataset's held-out test split, just scored live
instead of in a batch evaluation) or manual `/predict` calls. The
**Chargeback Center** additionally layers seeded/simulated chargeback and
refund *events* on top of those real predictions — there is no real
chargeback history anywhere in this project, and every chargeback shown is
labeled as seeded, in the UI, in the seeding script, and here. These are
three different, non-interchangeable things; none of them should be quoted
in place of another.

## Known limitations, stated honestly

- **A minor val/test boundary tie.** Three transactions share the exact
  same `Time` value at the validation/test split boundary, and the 85%
  index cut lands between them (2 in validation, 1 in test). This causes a
  small amount of cross-split contamination in that one test row's
  `amount_zscore` (2 of its 10,000-row rolling window come from
  validation), not future-information or label leakage. Given the window
  size, the practical effect is negligible. Full writeup: `docs/methodology.md`.
- **Content-hash dedup only covers the no-explicit-ID case.** If a client
  supplies its own `transaction_id`, a second submission with that same ID
  is rejected (409); if no ID is supplied, identical *content* is deduped
  by hash and the original prediction is returned. An explicit, distinct ID
  on identical content still creates a second row — the client is treated
  as explicitly asserting a new event in that case.
- **No return/refund/chargeback prediction models.** This project detects
  and explains *fraud risk at transaction time*, and separately assembles
  evidence *after* a chargeback occurs — it does not attempt to predict
  which transactions will be refunded or charged back, because no labeled
  return/chargeback dataset exists to train or validate such a model
  against. Building one on invented labels would be worse than not having
  it.
- **No customer data model.** The chargeback evidence responder reports
  "not available" for customer information on every single evidence
  package, rather than inventing a plausible-looking customer record — this
  system was never given any customer/account data to begin with.
- **`transaction` and `risk_prediction` are the same underlying record** in
  the evidence package API (see `api/services/evidence_service.py`) — there
  is no separate transactions table; the prediction row written at
  `/predict` time holds both a transaction's own fields and the model's
  risk assessment together. Exposed as two named fields to match the
  spec's described lookup chain, but they are not two independent sources.
  Stated in the API response itself (`data_model_note`), not just here.
- **Fraud-rate baseline is a static training-set measurement, not a live
  rolling one.** The spike detector compares recent traffic against the
  model's own predicted HIGH-tier rate on the training split (~0.20%),
  computed once at startup — deliberately not a live rolling baseline,
  which would be unstable at hackathon-scale traffic volume and could be
  silently poisoned by an earlier undetected spike.
- **Spike/severity thresholds (z ≥ 3.0, and the LOW/MEDIUM/HIGH bands) are
  reasonable, conventional defaults, not statistically fitted** — there is
  no labeled history of real fraud spikes to fit them against.
  `expected_financial_loss` on the Threshold Simulator page is similarly
  built on **placeholder** unit costs (false-positive cost 5, false-negative
  cost 100), not calibrated real currency figures.
- **Repeated `simulate.py --spike` runs eventually reuse the same rows.**
  The spike burst always picks the highest-probability test-set rows, and
  content-hash dedup (see above) means re-running it — or running it after
  `seed_chargebacks.py`, which claims the top 3 for its own demo — returns
  the *existing* prediction for any row already sent, with its original
  timestamp. Enough reused (old-timestamped) rows in a burst can make the
  rolling window fail to register a fresh spike on a repeat rehearsal --
  and this has a **hard ceiling, not a "use a bigger `--spike-size`"
  workaround**: the entire test split has only **40 rows** at or above
  the HIGH-risk threshold. A rehearsal-heavy audit session confirmed this
  directly and live -- `--spike-size 10` failed on a second consecutive
  run, and continued testing exhausted the full 40-row pool, at which
  point `--spike-size 30` failed completely too. `--count 0` (skips an
  unrelated 12-row normal-traffic warmup) plus a generous `--spike-size`
  is fine for a small number of rehearsals, but the only *reliable* fix
  once rows are claimed is resetting the database (`docker compose down`,
  delete `data/predictions.db`, `docker compose up`, redo the pre-show
  setup) -- do this once, right before the real presentation, not between
  every rehearsal. See `docs/demo_script.md` for the full procedure.
- **Single-machine SQLite, no auth, no rate limiting.** This is an
  intentional, stated hackathon-scope deferral, not an oversight — none of
  it was required by the brief, and adding it would have traded time away
  from the three things that were.

## Tech stack

**Backend:** Python, FastAPI, Pydantic, SQLAlchemy + SQLite, uvicorn.
**ML:** pandas, scikit-learn, XGBoost (Platt-calibrated), SHAP.
**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Recharts, React
Router.
**Infra:** Docker (multi-stage builds, nginx for the static frontend),
Docker Compose.
**Testing:** pytest (44 tests across the risk engine, API, anomaly
detector, model-info endpoint, threshold-simulator endpoint, and evidence
engine).
