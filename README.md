# Credit & Payments Risk Decision Engine

**Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk**

A focused risk decision system that turns borrower and transaction data into **underwriting decisions, fraud controls, expected-loss estimates, policy simulations, and model-validation evidence**. It is a decision engine, not a prediction notebook — model scores are translated into governed actions under loss, fraud, calibration, drift, and review-capacity constraints.

- **Live site:** https://credits-engine.netlify.app
- **Repository:** https://github.com/VM25/credits-lab

> Portfolio research project using public and clearly-labeled synthetic data. Modeled estimates, not realized losses. Not a production lending, fraud, or regulatory-compliance system.

---

## What it answers

| Question | Module |
|---|---|
| Who should get credit? | Underwriting engine → PD, risk grade, approve / review / decline, credit limit, reason codes |
| Which payments are risky? | Fraud & payments monitor → fraud score, action (approve / step-up / review / block), expected loss |
| How much could be lost? | Expected-loss engine → `PD × LGD × EAD`, by segment, under base and stressed conditions |
| Can the models be trusted? | Model-risk validation → calibration, drift, segments, Pass / Monitor / Fail verdicts |
| What if thresholds change? | Policy simulator → 180 precomputed scenarios trading growth against loss and review burden |

## Architecture

```
data ingestion → feature engineering → model training + calibration → decisioning
→ expected loss → validation → reporting outputs → React frontend
```

- **Backend:** Python 3, pandas, NumPy, scipy, scikit-learn, joblib, pytest. Modular `src/` package (`data`, `models`, `risk`, `validation`, `reporting`) driven by one orchestrator, `src/run_pipeline.py` (14 fail-fast phases, deterministic).
- **Frontend:** React 19 + TypeScript + Tailwind + Radix + Recharts + Vite. Reads only the reconciled static outputs in `data/outputs` — no hardcoded metrics.
- **Code evidence:** 30 Python source files, 20 test files, 40 test functions.

## Data sources

- **Credit:** LendingClub accepted loans (public, Kaggle `wordsforthewise/lending-club`), seeded stratified sample; rejected applicants for approval-funnel context.
- **Card payments:** Kaggle credit-card fraud (`mlg-ulb/creditcardfraud`) — real labels + `Amount` + `Time` + `V1..V28`; synthetic, clearly-labeled contextual features attached.
- **Macro:** FRED public series (unemployment, policy rate, inflation, credit-card delinquency, charge-off) — stress overlays only.
- **Stablecoin:** fully synthetic, seeded (secondary module).

Leakage is guarded structurally: only application-time credit fields are read; `fraud_flag` / `chargeback_loss` are excluded from fraud model features; a data-quality + leakage gate must pass before any output is written.

## Key results (from `data/outputs`)

- 94,999 credit applicants · 69,999 underwriting decisions · 80,000 payment transactions · 2,500 stablecoin transactions · 180 policy scenarios.
- Underwriting champion (logistic scorecard, calibrated): ROC-AUC ≈ 0.695 — verdict **Monitor** (usable, modest discrimination, disclosed).
- Fraud supervised model: PR-AUC ≈ 0.66, ROC-AUC ≈ 0.97, capture ≈ 0.81 at the review+block boundary — verdict **Pass**.
- Stablecoin AML-style scorer: discrimination AUC ≈ 0.87 vs. the synthetic label — verdict **Pass**.

## Run it

Requires Python 3 (`python3`) and Node. Kaggle API token at `~/.kaggle/kaggle.json` is needed to regenerate raw data.

```bash
# backend: regenerate all 25 reconciled outputs (deterministic)
python3 -m pip install -r requirements.txt
python3 -m src.run_pipeline

# tests
python3 -m pytest -q

# frontend (syncs data/outputs, serves the terminal)
cd frontend && npm install && npm run dev
```

`data/outputs` is committed, so the frontend renders immediately without re-running the pipeline.

## Assumptions & limitations

- `default_flag` is a **default / severe-delinquency proxy** (Charged Off / Default / Late 31–120 / charged-off "does not meet policy"), not pure charge-off default.
- Expected-loss dollars are **assumption-driven** (LGD/EAD/severity/stress are labeled assumptions), not observed losses from an active book.
- Card contextual features and the entire stablecoin domain are **synthetic**; the stablecoin label is synthetic.
- `amount_zscore_by_account` uses each account's full-window mean/std (mild temporal lookahead), disclosed.
- Macro variables inform stress overlays only; no individual-default causality is claimed.
- No real customer data, no real lending decisions, no regulatory-compliance claim.

## Deployment

The site lives in `frontend/` and deploys on Netlify from this repository (continuous deployment — pushing to `main` rebuilds and redeploys). Build: base `frontend`, command `npm run build`, publish `dist`.
