# 11_BUILD_PLAN.md

# Build Plan

## 1. Build Rule

Follow docs in order:

```text id="qz8f2o"
00_PROJECT_SCOPE.md
01_PROJECT_THESIS.md
02_DATA_SPEC.md
03_UNDERWRITING_STRATEGY_SPEC.md
04_FRAUD_PAYMENTS_RISK_SPEC.md
05_EXPECTED_LOSS_ENGINE_SPEC.md
06_MODEL_RISK_VALIDATION_SPEC.md
07_POLICY_SIMULATOR_SPEC.md
08_OUTPUTS_AND_REPORTING_SPEC.md
09_PRODUCT_REQUIREMENTS.md
10_DESIGN_SYSTEM.md
11_BUILD_PLAN.md
```

Do not skip docs.

Do not reinterpret scope.

---

## 2. Project Paths

Project root:

```text id="zbyuwu"
/Users/vatsal/Documents/credits-lab
```

Docs path:

```text id="chzd26"
/Users/vatsal/Documents/credits-lab/docs
```

Required structure:

```text id="2y9rlb"
data/raw
data/interim
data/processed
data/outputs
src/data
src/models
src/risk
src/validation
src/reporting
frontend
```

Do not create `README.md` unless explicitly requested by the user.

---

## 3. Phase 1 — Repository Setup

Create only required folders and project files.

Do:

```text id="j4su2e"
initialize Python environment
initialize frontend if needed
create data folders
create src folders
create config files
```

Do not build UI first.

Do not create placeholder dashboards.

Do not create README.

---

## 4. Phase 2 — Data Layer

Implement data ingestion and cleaning.

Build:

```text id="7y98cc"
credit data pipeline
payment transaction pipeline
stablecoin transaction pipeline
macro / stress input pipeline
data quality report
```

Required outputs:

```text id="cj5riv"
processed_credit_applicants.csv
processed_payment_transactions.csv
processed_stablecoin_transactions.csv
macro_stress_inputs.csv
data_quality_report.csv
```

Stop if leakage is detected.

---

## 5. Phase 3 — Underwriting Engine

Build credit decision module.

Implement:

```text id="orky35"
logistic regression champion
gradient boosting challenger
PD calibration
risk grades
approve / review / decline policy
credit-limit recommendation
reason codes
```

Required outputs:

```text id="9cy2we"
underwriting_decisions.csv
underwriting_decisions.json
underwriting_policy_summary.json
```

Do not use post-origination leakage.

---

## 6. Phase 4 — Fraud & Payments Engine

Build transaction-risk module.

Implement:

```text id="2afiqd"
rules engine
supervised fraud model if labels exist
anomaly model
fraud score
payment action mapping
manual-review queue
expected fraud loss
```

Required outputs:

```text id="jroohg"
fraud_alerts.csv
fraud_alerts.json
fraud_policy_summary.json
```

Do not use accuracy as the main fraud metric.

---

## 7. Phase 5 — Stablecoin Risk Module

Build secondary payments-risk module.

Implement:

```text id="t8u1o9"
wallet-risk scoring
velocity features
counterparty-risk features
risky exposure proxy
stablecoin action mapping
```

Required outputs:

```text id="qlyuyg"
stablecoin_alerts.csv
stablecoin_alerts.json
```

Use only:

```text id="d5zfah"
AML-style risk indicators
```

Do not build crypto trading, DeFi, NFT, yield, or token-price logic.

---

## 8. Phase 6 — Expected Loss Engine

Build loss translation layer.

Implement:

```text id="x0wl92"
credit expected loss
fraud expected loss
stablecoin risk exposure
segment loss views
base / moderate / severe stress cases
policy loss comparison
```

Required outputs:

```text id="15kaxr"
expected_loss_applicant_level.csv
expected_loss_summary.json
expected_loss_by_segment.json
stress_loss_summary.json
policy_loss_comparison.json
```

All assumptions must be labeled.

---

## 9. Phase 7 — Model Risk Validation

Build validation layer.

Implement:

```text id="6o6m0w"
credit model validation
fraud model validation
stablecoin risk validation
calibration checks
drift checks
segment checks
explainability checks
champion vs challenger comparison
model verdicts
```

Required outputs:

```text id="xvfovn"
model_validation_summary.json
credit_model_validation.csv
fraud_model_validation.csv
stablecoin_model_validation.csv
champion_challenger_comparison.json
model_risk_verdicts.json
```

Verdicts allowed:

```text id="hak0vz"
Pass
Monitor
Fail
```

---

## 10. Phase 8 — Policy Simulator Data

Build simulator backend data.

Implement configurable grids for:

```text id="7z86l6"
credit PD thresholds
fraud thresholds
stablecoin thresholds
review capacity
stress scenarios
loss assumptions
```

Required outputs:

```text id="j7hvy8"
policy_simulator_inputs.json
policy_simulator_results.json
policy_threshold_grid.csv
```

Do not fake simulator values in frontend.

---

## 11. Phase 9 — Reporting Layer

Create final reporting outputs.

Required outputs:

```text id="bmp3b1"
risk_command_center.json
methodology_summary.json
all CSV outputs
all JSON outputs
```

Verify:

```text id="bce4x3"
applicant totals reconcile
transaction totals reconcile
segment totals reconcile
loss totals reconcile
validation verdicts match metrics
```

Stop if outputs do not reconcile.

---

## 12. Phase 10 — Frontend Build

Build frontend only after backend outputs exist.

Required sections:

```text id="b1o47v"
Hero / Project Overview
Risk Command Center
Underwriting Decision Engine
Policy Simulator
Fraud & Payments Monitor
Stablecoin Risk Monitor
Expected Loss Engine
Model Risk & Validation
Stress Testing
Evidence & Methodology
```

All metrics must load from:

```text id="z7o69s"
data/outputs
```

No hardcoded frontend numbers.

---

## 13. Phase 11 — Design Execution

Before UI implementation, follow `10_DESIGN_SYSTEM.md`.

Mandatory:

```text id="q6g3yu"
use all available required design skills/plugins/MCPs
do not use personal design taste
do not violate forbidden fonts
do not violate forbidden colors
do not violate forbidden UI patterns
```

If required design tools are unavailable, stop and report.

Do not substitute generic design judgment.

---

## 14. Phase 12 — Final QA

Run checks for:

```text id="61zbmy"
target leakage
data quality
model metrics
calibration
loss reconciliation
policy simulator consistency
frontend data traceability
copy restrictions
forbidden UI violations
README absence
```

Do not present final build if any critical check fails.

---

## 15. Required Final State

The final project must contain:

```text id="nel0b9"
working Python risk engine
clean processed data
complete data/outputs folder
frontend reading static JSON
traceable charts
model validation evidence
policy simulator
methodology disclosure
no README unless requested
```

---

## 16. Forbidden Build Behavior

Do not:

```text id="i4pjjv"
start with frontend
invent metrics
hardcode dashboard values
hide weak model results
use forbidden UI choices
turn stablecoin module into crypto investing
claim AML compliance
claim production readiness
create README.md
```

---

## 17. Final Acceptance Standard

The build is complete only if the project clearly proves:

```text id="s356yz"
borrower and transaction data can be translated into underwriting decisions, fraud controls, expected-loss estimates, and model-risk validation evidence.
```

No other story is allowed.
