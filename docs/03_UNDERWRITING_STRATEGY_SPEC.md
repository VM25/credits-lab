# 03_UNDERWRITING_STRATEGY_SPEC.md

# Underwriting Strategy Specification

## 1. Module Purpose

Build the credit decisioning module.

It must answer:

```text id="0yrhe3"
Should this applicant be approved, reviewed, or declined?
```

The module must convert borrower data into:

```text id="npcoo0"
default probability
risk grade
credit decision
credit-limit recommendation
expected loss
reason codes
```

This is not only a default-prediction model.

---

## 2. Required Inputs

Use the processed credit dataset from:

```text id="4fcjie"
data/processed/underwriting_model_dataset.csv
```

Required fields:

```text id="30z90c"
applicant_id
application_date
loan_amount
annual_income
debt_to_income
employment_length
credit_grade
interest_rate
loan_purpose
home_ownership
delinquency_history
revolving_utilization
open_accounts
default_flag
loss_amount_if_default
```

Allowed engineered fields:

```text id="v5c45m"
income_to_loan_ratio
debt_burden_score
credit_utilization_band
loan_size_band
credit_grade_numeric
prior_delinquency_flag
application_vintage
```

Do not use post-origination fields for initial underwriting.

---

## 3. Target Variable

Primary target:

```text id="5fsg8x"
default_flag
```

Definition:

```text id="plmxmo"
1 = borrower defaults or reaches severe delinquency
0 = borrower performs
```

Document the exact dataset-specific definition before modeling.

Do not silently mix default, charge-off, late payment, and settlement outcomes.

---

## 4. Model Stack

Build two models.

### A. Champion Model

Use:

```text id="nrvud7"
logistic regression scorecard
```

Purpose:

```text id="zzzwkx"
explainable baseline underwriting model
```

Required:

* standardized features
* interpretable coefficients
* predicted probability of default
* reason-code support

### B. Challenger Model

Use:

```text id="b116ae"
gradient boosting model
```

Purpose:

```text id="73450j"
stronger nonlinear benchmark
```

Required:

* probability output
* calibration check
* feature importance
* comparison against champion

Do not use deep learning.

---

## 5. Probability of Default

Each applicant must receive:

```text id="h2a50l"
PD = predicted probability of default
```

PD must be calibrated before policy use.

Required calibration checks:

```text id="q087mh"
Brier score
calibration curve
decile default table
predicted vs actual default by risk band
```

Do not use raw model scores as final PD unless calibration is acceptable.

---

## 6. Risk Grades

Convert PD into risk grades.

Default bands:

```text id="5ibgyi"
A: PD < 2%
B: 2% ≤ PD < 5%
C: 5% ≤ PD < 10%
D: 10% ≤ PD < 20%
E: PD ≥ 20%
```

These bands are starting assumptions.

Final bands may be adjusted only if validation supports the change.

---

## 7. Decision Policy

Map PD to decision.

Default policy:

```text id="jx27te"
Approve: PD < 6%
Review: 6% ≤ PD < 12%
Decline: PD ≥ 12%
```

Required outputs:

```text id="60co8q"
approval_rate
review_rate
decline_rate
default_rate_by_decision
expected_loss_by_decision
```

Thresholds must be configurable for the policy simulator.

---

## 8. Credit-Limit Recommendation

Assign credit limit using risk and affordability.

Inputs:

```text id="8n98il"
PD
annual_income
debt_to_income
loan_amount
risk_grade
```

Simple rule acceptable:

```text id="nq63d8"
lower PD + stronger income coverage = higher approved limit
higher PD + weaker income coverage = lower approved limit
```

Required output:

```text id="b0t46k"
recommended_credit_limit
```

Do not claim this is an institutional credit-line model.

---

## 9. Expected Loss Link

For every approved or reviewed applicant, calculate:

```text id="iiexx8"
Expected Loss = PD × LGD × EAD
```

Required fields:

```text id="d133qw"
PD
LGD
EAD
expected_loss
expected_loss_rate
```

LGD and EAD assumptions must come from `05_EXPECTED_LOSS_ENGINE_SPEC.md`.

---

## 10. Reason Codes

Every decline or review decision must include reason codes.

Allowed reason-code drivers:

```text id="xr9bvn"
high debt-to-income
low income-to-loan coverage
high revolving utilization
prior delinquency
weak credit grade
large loan amount
high predicted default risk
```

Reason codes must be explainable.

Do not generate vague reasons such as:

```text id="d9mt2p"
model says risky
AI decision
complex pattern detected
```

---

## 11. Required Outputs

Create:

```text id="mcyx0u"
data/outputs/underwriting_decisions.csv
data/outputs/underwriting_decisions.json
data/outputs/underwriting_policy_summary.json
```

Each applicant row must include:

```text id="5ua1y7"
applicant_id
PD
risk_grade
decision
recommended_credit_limit
LGD
EAD
expected_loss
top_reason_1
top_reason_2
top_reason_3
model_used
```

---

## 12. Required Charts

Generate frontend-ready data for:

```text id="3yo38b"
PD distribution
risk-grade distribution
approval / review / decline mix
approval rate vs expected loss
default rate by risk grade
expected loss by risk grade
top reason-code frequency
champion vs challenger PD comparison
```

Charts must support the frontend.

No decorative charts.

---

## 13. Validation Requirements

Minimum validation:

```text id="rmjbmb"
ROC-AUC
PR-AUC
Brier score
calibration curve
confusion matrix at policy threshold
decile default table
approval-rate / loss-rate tradeoff
segment-level performance
```

Model validation details belong in:

```text id="6yffr5"
06_MODEL_RISK_VALIDATION_SPEC.md
```

This module must still export all validation inputs.

---

## 14. Leakage Rules

Forbidden features:

```text id="2ziin6"
future repayment status
recoveries
collections
settlement information
post-default fields
post-origination performance
future delinquency fields
```

If leakage is detected, stop and fix the dataset.

Do not continue with contaminated results.

---

## 15. Build Boundary

Do not create `README.md` unless explicitly requested by the user.

Do not build frontend components from this doc alone.

This doc only defines underwriting logic, outputs, and constraints.
