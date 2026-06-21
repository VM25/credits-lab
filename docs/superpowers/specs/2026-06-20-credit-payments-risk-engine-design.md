# Credit & Payments Risk Decision Engine — Design Spec

**Date:** 2026-06-20
**Status:** Approved (scope) — pending spec review
**Project root:** `/Users/vatsal/Documents/credits-lab`
**Authority:** `docs/00_PROJECT_SCOPE.md` … `docs/11_BUILD_PLAN.md` are the source of truth. This spec operationalizes them; it does not reinterpret or expand scope. Where this spec and the numbered docs disagree, the numbered docs win.

---

## 1. The single story (non-negotiable)

The build proves exactly one claim and no broader one:

> Borrower and transaction data are translated into underwriting decisions, fraud controls, expected-loss estimates, and model-risk validation evidence.

No claims of production readiness, institutional-grade modeling, AML compliance, guaranteed detection, real-time deployment, or "optimal" policy.

## 2. Locked decisions (from brainstorming)

1. **Direction:** clean rebuild — keep nothing from the prior build. Prior tree preserved only as git baseline (commit `ad13efd`); rebuild replaces it.
2. **Data:** hybrid sourcing (see §5), exactly as specified by the user:
   - Credit → public **LendingClub** accepted loans (primary); rejected loans sampled + clearly-labeled synthetic rejects for reject-inference/policy context.
   - Card payments → public **Kaggle** `mlg-ulb/creditcardfraud` (real labels); synthetic, clearly-labeled contextual fields attached at transaction time.
   - Stablecoin → fully **synthetic** (secondary).
   - Macro → public **FRED** series (stress overlays only).
3. **ML stack:** **scikit-learn** (LogisticRegression, GradientBoosting, IsolationForest/LOF, `sklearn.metrics`, `sklearn.calibration`). Adds `scikit-learn` + `joblib` to `requirements.txt`.
4. **Git:** local only. `git init` done; local commits for spec/plan/build checkpoints. **No** GitHub repo, **no** remote, **no** push.
5. **Outputs:** create every required CSV/JSON from the docs and nothing else. Chart-ready data lives **inside** the required JSON files; any added internal structure is documented in `methodology_summary.json` (user clarification).

## 3. Guardrails (enforced every phase)

- **Backend before frontend.** Frontend begins only after `data/outputs` is complete and reconciled.
- **No hardcoded frontend numbers.** Every UI value traces to a file in `data/outputs`.
- **No `README.md`** unless the user explicitly asks.
- **Honesty / labeling:** real data labeled real (dataset name + snapshot/pull date); synthetic data and engineered features labeled synthetic in outputs, `methodology_summary.json`, and the UI disclaimer. Never present synthetic as observed history; never present public sample as proprietary bank data.
- **Determinism:** one global seed (`src/config.py`); pinned `random_state` on all models/splits/samples; recorded data snapshot (dataset versions + FRED pull date) in `methodology_summary.json`.
- **Secret handling:** Kaggle token stays in `~/.kaggle/kaggle.json` (chmod 600). Never committed (gitignored), never written to repo/outputs/memory.

### 3.1 Hard stop conditions (halt and report — do not continue)

- target leakage detected
- output totals do not reconcile (applicant / transaction / segment / loss; verdicts vs metrics)
- required validation missing or not measurable (e.g., calibration cannot be computed)
- an unsupported claim would be emitted
- a mandatory design capability is unavailable at use time
- an unresolved doc conflict (conflicts already resolved by user clarification are applied, not stopped on — see §9)

## 4. Repository structure (doc 11 §2 — real modules, focused files)

```
src/
  config.py              # paths, global seed, policy thresholds (doc defaults), LGD/EAD/severity/stress assumptions
  data/
    ingest_credit.py     # LendingClub download + sample + clean + leakage filter
    ingest_payments.py   # Kaggle fraud download + real fields + synthetic labeled context
    ingest_stablecoin.py # synthetic stablecoin generation
    ingest_macro.py      # FRED CSV pulls
    quality.py           # data_quality_report + leakage checks + schema validation
    splits.py            # time-aware 70/15/15 splits
  models/
    scorecard.py         # logistic regression champion (+ reason-code coefficients)
    gbm.py               # gradient boosting challenger
    calibration.py       # PD calibration (isotonic/Platt) + Brier/curve
    anomaly.py           # IsolationForest / LOF
    metrics.py           # ROC-AUC, PR-AUC, Brier, KS, confusion, PSI helpers
  risk/
    underwriting.py      # PD -> grade -> decision -> limit -> reason codes
    fraud.py             # rules + supervised + anomaly -> score -> action -> review queue
    stablecoin.py        # wallet-risk scoring -> action (AML-style indicators)
    expected_loss.py     # EL=PD*LGD*EAD, fraud loss, stablecoin exposure, segments, stress
    policy_simulator.py  # threshold grid + scenario results + constraint enforcement + warnings
  validation/
    validate.py          # per-model metrics, calibration, drift/PSI, segments, champion/challenger, verdicts
  reporting/
    command_center.py    # risk_command_center.json
    methodology.py       # methodology_summary.json
    reconcile.py         # reconciliation gate + required-output check
    writers.py           # CSV/JSON writers (deterministic, rounded)
  run_pipeline.py        # orchestrator: runs phases in doc order; fails fast on stop conditions
data/{raw,interim,processed,outputs}
frontend/                # Vite + React + TS (rebuilt fresh)
```

Each module has one clear purpose and can be reasoned about independently. `run_pipeline.py` is the single entry point that produces a complete, reconciled `data/outputs`.

## 5. Data layer

### 5.1 Credit (LendingClub — real, sampled)
- Source: `wordsforthewise/lending-club` → `accepted_2007_to_2018Q4.csv.gz`. Chunked random sample (seeded) to ~60–80k rows for a workable, reproducible build. Rejected file sampled for context; clearly-labeled synthetic rejected applicants added for reject-inference/policy simulation.
- Map to doc 02/03 schema: `applicant_id, application_date(issue_d), loan_amount(loan_amnt), annual_income(annual_inc), debt_to_income(dti), employment_length(emp_length), credit_grade(grade), interest_rate(int_rate), loan_purpose(purpose), home_ownership(home_ownership), delinquency_history(delinq_2yrs), revolving_utilization(revol_util), open_accounts(open_acc), default_flag, loss_amount_if_default`.
- **Target `default_flag`:** 1 = `Charged Off`, `Default`, `Late (31-120 days)`, `Does not meet the credit policy. Status:Charged Off`; 0 = `Fully Paid`. **Drop** `Current`, `In Grace Period`, `Late (16-30 days)`, and other in-progress/ambiguous statuses. Exact definition recorded in `methodology_summary.json`.
- `loss_amount_if_default`: estimated as `loan_amount × LGD` (assumption, labeled) — not derived from post-default recoveries.
- **Leakage allowlist (doc 02 §4, doc 03 §14):** keep only application-time fields. Drop `recoveries`, `collection_recovery_fee`, `total_pymnt*`, `total_rec_*`, `last_pymnt_*`, `out_prncp*`, `next_pymnt_d`, post-origination status/behavior, and any field unavailable at application.
- Engineered (labeled): `income_to_loan_ratio, debt_burden_score, credit_utilization_band, loan_size_band, credit_grade_numeric, prior_delinquency_flag, application_vintage`.

### 5.2 Card payments (Kaggle — real labels + synthetic context)
- Source: `mlg-ulb/creditcardfraud` → `creditcard.csv` (284,807 rows; `Time`, `Amount`, `Class`, `V1–V28`; ~0.172% fraud). `fraud_flag = Class`.
- Real fields kept: `Time`, `Amount`, `V1–V28` (model features), `Class`.
- **Synthetic, clearly-labeled** contextual fields attached at transaction time to satisfy doc 02/04 schema: `transaction_id, account_id, merchant_category, merchant_risk_band, location_proxy, device_proxy, account_age_days, transaction_count_24h, amount_count_24h, chargeback_loss`. 24h velocity derived from real `Time` ordering within synthetic account assignment.
- Engineered (labeled): `velocity_1h, velocity_24h, amount_zscore_by_account, merchant_risk_score, new_device_flag, new_location_flag, night_transaction_flag, high_amount_flag, account_tenure_band`.
- Fraud is imbalanced — accuracy is never the headline metric.

### 5.3 Stablecoin (synthetic, secondary)
- Fully synthetic, seeded. Fields per doc 02/04: `wallet_id, counterparty_wallet_id, transaction_time, token_type, amount_usd, wallet_age_days, inflow_24h, outflow_24h, transaction_count_24h, counterparty_risk_score, risky_address_exposure_flag, stablecoin_risk_label`.
- Engineered: `wallet_velocity, inflow_outflow_ratio, counterparty_concentration, round_trip_proxy, large_transfer_flag, new_counterparty_flag, risk_exposure_score`.
- Payments-risk only. No crypto trading / DeFi / NFT / yield / token-price. "AML-style risk indicators," never "AML compliance."

### 5.4 Macro (FRED — real)
- Public CSV endpoints (no key): `UNRATE` (unemployment), `FEDFUNDS` (policy rate), `CPIAUCSL` → YoY `inflation_rate`, `DRCCLACBS` (consumer-credit/CC delinquency), `CORCCACBS` (CC charge-off). Pull date recorded.
- Used only for stress overlays / loss sensitivity. No individual-default causality claims.

### 5.5 Splits & processed outputs
- Time-aware **70 / 15 / 15** by date (credit `issue_d`; card by `Time`). Thresholds never tuned on the test set. Limitation stated where dates are weak.
- **Processed datasets** (`data/processed/`, doc 02 §9): `processed_credit_applicants.csv, processed_payment_transactions.csv, processed_stablecoin_transactions.csv, macro_stress_inputs.csv, underwriting_model_dataset.csv, fraud_model_dataset.csv, validation_dataset.csv`.
- **Data quality / leakage** (`data/outputs/data_quality_report.csv`, doc 08 §11): row/column counts, missing, duplicate IDs, target rate, date range, leakage_check_status, schema_check_status. **Build stops if leakage status = failed.**

## 6. Engines (built in user-specified order; sklearn)

1. **Underwriting (doc 03)** — logistic-regression scorecard (champion) + gradient boosting (challenger); PD calibration (isotonic/Platt) with Brier + calibration curve; risk grades A–E (PD <2/2–5/5–10/10–20/≥20%); decisions approve/review/decline (PD <6 / 6–12 / ≥12%, configurable); credit-limit rule from PD + affordability; explainable reason codes (no vague/black-box reasons). EL link via §6.4. Outputs: `underwriting_decisions.csv`, `underwriting_decisions.json`, `underwriting_policy_summary.json`.
2. **Fraud & payments (doc 04)** — rules engine + supervised model (PR-AUC headline) + anomaly model (IsolationForest/LOF); action map approve/step-up/review/block (0.35/0.60/0.80, configurable); expected fraud loss = `fraud_probability × amount × loss_severity(90%)`; capacity-aware ranked manual-review queue; cost-by-threshold views. Outputs: `fraud_alerts.csv`, `fraud_alerts.json`, `fraud_policy_summary.json`.
3. **Stablecoin (doc 04 §4/§8)** — wallet-risk scoring + velocity/counterparty features; actions normal/monitor/review/high-risk (0.40/0.65/0.85); risky-exposure proxy. Outputs: `stablecoin_alerts.csv`, `stablecoin_alerts.json`.
4. **Expected loss (doc 05)** — credit EL = PD×LGD×EAD (LGD 35/55/75% by risk; default 55%; EAD = loan_amount for installment, limit×util(65%) for revolving); fraud EL; stablecoin exposure proxy; net_expected_value = interest_rate×EAD − EL (labeled, partial); segment loss views; **Base/Moderate/Severe** stress (PD ×1/1.25/1.6, LGD ×1/1.10/1.25, fraud ×1/1.20/1.50; PD capped at 1); policy loss comparison. Validation: PD∈[0,1], LGD∈[0,1], EAD≥0, EL≥0, stressed PD≤1, **segment totals reconcile to portfolio (stop if not)**. Outputs: `expected_loss_applicant_level.csv`, `expected_loss_summary.json`, `expected_loss_by_segment.json`, `stress_loss_summary.json`, `policy_loss_comparison.json`.
5. **Model-risk validation (doc 06)** — performance (ROC-AUC, PR-AUC, Brier, KS, confusion), calibration (curve + decile default table + predicted-vs-actual by band), stability/drift (PSI bands <0.10 / 0.10–0.25 / ≥0.25), segment performance, champion-vs-challenger (not auto-highest-AUC — weighs calibration + explainability + stability), explainability (coefficients/importance/permutation/rule triggers; no black-box reasons), per-model verdict **Pass/Monitor/Fail** with one-sentence reason. Outputs: `model_validation_summary.json`, `credit_model_validation.csv`, `fraud_model_validation.csv`, `stablecoin_model_validation.csv`, `champion_challenger_comparison.json`, `model_risk_verdicts.json`.
6. **Policy simulator data (doc 07)** — precomputed threshold grid + scenario results; constraint enforcement (approve<review<decline; fraud approve<step-up<review<block; stablecoin monitor<review<high-risk; PD/LGD∈[0,1]; multipliers>0; capacity≥0); **specific** model-risk warnings (e.g., "manual review volume exceeds capacity by 18%"), never "Risk is high." Outputs: `policy_simulator_inputs.json`, `policy_simulator_results.json`, `policy_threshold_grid.csv`.
7. **Reporting (doc 08)** — `risk_command_center.json` (portfolio KPIs), `methodology_summary.json` (sources, synthetic disclosure, model list, features, split method, loss/stress assumptions, validation methods, known limitations, chart-data embedding map), all chart-ready JSON; **reconciliation gate** + required-output check (stop if any required file missing or totals don't reconcile).

## 7. Canonical output contract (doc 08 is authoritative)

**`data/outputs/` CSV (9):** `underwriting_decisions.csv, fraud_alerts.csv, stablecoin_alerts.csv, expected_loss_applicant_level.csv, credit_model_validation.csv, fraud_model_validation.csv, stablecoin_model_validation.csv, policy_threshold_grid.csv, data_quality_report.csv`.

**`data/outputs/` JSON (16):** `risk_command_center.json, underwriting_decisions.json, underwriting_policy_summary.json, fraud_alerts.json, stablecoin_alerts.json, fraud_policy_summary.json, expected_loss_summary.json, expected_loss_by_segment.json, stress_loss_summary.json, policy_loss_comparison.json, policy_simulator_inputs.json, policy_simulator_results.json, model_validation_summary.json, champion_challenger_comparison.json, model_risk_verdicts.json, methodology_summary.json`.

**Chart-data embedding rule (user clarification + reconciliation of doc 06 §7 vs doc 08):** doc 06 §7 names `calibration_curve.json` and `decile_default_table.csv` as calibration artifacts, but doc 08 (the canonical output contract that enumerates "all CSV/JSON outputs") does not list them as standalone files. Resolution: the calibration curve and decile default table are **embedded inside `model_validation_summary.json`** (decile table also surfaced within `credit_model_validation.csv`), not emitted as separate files. This mapping is documented in `methodology_summary.json`. No output files beyond the lists above are created.

**Required-output check:** before any frontend work, assert all 25 files (+ 7 processed datasets) exist and are non-empty.

## 8. Frontend (only after outputs reconcile)

- **Stack:** Vite + React + TypeScript + Tailwind + **shadcn/ui (de-SaaS'd — rounded-card/default SaaS aesthetics overridden per doc 10 §7)** + framer-motion (functional motion only) + Recharts. Static JSON load from `data/outputs`; no backend server.
- **Data wiring:** `data/outputs` is the single source; a build step copies/symlinks it into the frontend's static dir so the SPA fetches the real files. No metric is inlined in TSX.
- **Sections (exactly 10; doc 09 §3 / doc 11 §12), no filler:** Hero/Project Overview · Risk Command Center · Underwriting Decision Engine · Policy Simulator · Fraud & Payments Monitor · Stablecoin Risk Monitor · Expected Loss Engine · Model Risk & Validation · Stress Testing · Evidence & Methodology.
- Required title "Credit & Payments Risk Decision Engine" + subtitle "Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk".
- **Interactions limited to doc 09 §14:** policy sliders, threshold selectors, stress-scenario selector, table row selection, module tabs, chart hover. Simulator reads the precomputed grid — real interactivity, no fake recompute.
- Desktop/laptop primary; tablet secondary; mobile readable fallback. Density not sacrificed for mobile.
- **Copy rules (doc 09 §15 / doc 10 §11):** allowed risk language only; forbidden terms banned (production-ready, institutional-grade, guaranteed, AML compliance, optimal policy, AI-powered magic, real-time bank).

## 9. Design-system execution (doc 10 — gating the UI)

- Before writing any UI, run the **mandatory** design skills: `emil-design-eng`, `frontend-design`, `design-taste-frontend`, `ui-ux-pro-max`, `senior-frontend`; use the **shadcn MCP** for components; install framer-motion via npm. Availability verified during brainstorming (skills + shadcn MCP + Figma MCP present). **If any is unavailable at use time, stop and report — do not substitute personal taste.**
- Typography + palette are **derived by these skills within the forbidden-font/color lists**, then presented to the user for approval **before** UI build. Constraints: no forbidden font families (or their variants); Source Code Pro only for all-caps; no forbidden dark/light colors; no black/white-only theme; no forbidden UI patterns (rounded SaaS cards, cybersecurity/neon/terminal/crypto aesthetics, decorative charts/curves, generic KPI tiles, mesh backgrounds).
- Charts must explain risk and trace to `data/outputs`; motion only to communicate state change (threshold/decision/verdict/stress/row-focus).

## 10. Final QA gate (doc 11 §14)

Automated checks before declaring done: target leakage, data quality, model metrics present, calibration measured, loss reconciliation, simulator consistency, frontend data traceability (no hardcoded numbers), copy-restriction scan, forbidden-font/color/UI scan, **README-absence** check. Do not present the build if any critical check fails.

## 11. Reproducibility & provenance

- `requirements.txt`: pandas, numpy, scipy, scikit-learn, joblib, requests, kaggle.
- One command rebuilds everything: `python -m src.run_pipeline` → populated, reconciled `data/outputs`.
- `methodology_summary.json` records: dataset names + versions + FRED pull date, synthetic-data disclosure, model list, feature summary, split method, LGD/EAD/severity/stress assumptions, validation methods, known limitations, chart-data embedding map.

## 12. Out of scope / non-goals (docs 00 §5, 01 §6)

Not a Kaggle classifier, default-prediction notebook, crypto/DeFi/NFT/token-price project, full banking simulator, portfolio-allocation tool, marketing landing page, black-box demo, or generic fintech dashboard. No features beyond the docs. No README unless requested.

## 13. Implementation phasing (feeds writing-plans)

P1 repo setup (modules, config, requirements, remove prior build) → P2 data layer (+quality/leakage gate) → P3 underwriting → P4 fraud/payments → P5 stablecoin → P6 expected loss → P7 model-risk validation → P8 policy simulator data → P9 reporting (+reconciliation gate) → **outputs complete** → P10 design-system tokens (skills, user approval) → P11 frontend build → P12 final QA. Backend (P1–P9) fully precedes frontend (P10–P11).
