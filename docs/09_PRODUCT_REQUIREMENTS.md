# 09_PRODUCT_REQUIREMENTS.md

# Product Requirements

## 1. Product Purpose

Build a frontend risk decision terminal for:

```text id="smojik"
credit underwriting
fraud monitoring
expected loss
model validation
policy simulation
stablecoin payments-risk monitoring
```

The app must explain decisions, not decorate models.

---

## 2. Product Standard

The product must feel like:

```text id="oimimu"
a risk decision terminal
```

Not:

```text id="2n1a7v"
a fintech landing page
a generic ML dashboard
a crypto dashboard
a bank marketing website
```

Every section must show a risk decision, loss estimate, validation result, or policy tradeoff.

---

## 3. Required Pages / Sections

Single-page app preferred.

Required sections:

```text id="bch53n"
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

No filler sections.

---

## 4. Hero / Project Overview

Purpose:

```text id="r6taej"
Explain what the system does in one screen.
```

Must show:

```text id="b9ewxl"
project title
one-line thesis
four module labels
primary risk KPIs
data / model disclaimer
```

Required title:

```text id="ntfatn"
Credit & Payments Risk Decision Engine
```

Required subtitle:

```text id="ez44p1"
Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk
```

---

## 5. Risk Command Center

Purpose:

```text id="18bzka"
Show portfolio-level risk state.
```

Must show:

```text id="j2g1hj"
total applicants
approval rate
review rate
decline rate
average PD
approved exposure
expected credit loss
expected fraud loss
stablecoin risk exposure
manual-review volume
model verdict summary
```

Data source:

```text id="nv7w7b"
risk_command_center.json
```

No hardcoded metrics.

---

## 6. Underwriting Decision Engine

Purpose:

```text id="bcujxm"
Show how applicant data becomes a credit decision.
```

Must show:

```text id="grzqjv"
applicant table
PD
risk grade
approve / review / decline decision
recommended credit limit
expected loss
top reason codes
```

Required chart views:

```text id="a0682d"
PD distribution
risk-grade distribution
approval mix
expected loss by risk grade
top decline reasons
```

Data source:

```text id="wgnxx5"
underwriting_decisions.json
underwriting_policy_summary.json
```

---

## 7. Policy Simulator

Purpose:

```text id="6tbucl"
Show how threshold changes affect growth and loss.
```

Required controls:

```text id="bpowez"
approval PD cutoff
review band
fraud threshold
manual-review capacity
stablecoin risk threshold
stress scenario
```

Must update:

```text id="a1qvf9"
approval rate
decline rate
expected credit loss
expected fraud loss
stablecoin risk exposure
manual-review volume
model-risk warnings
```

Data source:

```text id="9xqpbw"
policy_simulator_inputs.json
policy_simulator_results.json
```

No fake interactivity.

---

## 8. Fraud & Payments Monitor

Purpose:

```text id="097tlj"
Show transaction-risk scoring and action selection.
```

Must show:

```text id="a96ql1"
transaction stream
fraud score
anomaly score
payment action
expected fraud loss
manual-review priority
top risk drivers
```

Required actions:

```text id="s784do"
Approve
Step-up verification
Manual review
Block
```

Data source:

```text id="u3bata"
fraud_alerts.json
fraud_policy_summary.json
```

---

## 9. Stablecoin Risk Monitor

Purpose:

```text id="pl90vb"
Show stablecoin payments-risk monitoring as a secondary module.
```

Must show:

```text id="e6l2pp"
wallet ID
counterparty wallet
amount USD
stablecoin risk score
risk action
risk exposure score
top risk drivers
```

Allowed language:

```text id="2v38t1"
AML-style risk indicators
```

Forbidden language:

```text id="dvmikl"
AML compliance platform
crypto trading system
blockchain investment dashboard
```

Data source:

```text id="2y0t06"
stablecoin_alerts.json
```

---

## 10. Expected Loss Engine

Purpose:

```text id="7yp8lb"
Show how risk scores become financial loss estimates.
```

Must show formula:

```text id="7x9s0g"
Expected Loss = PD × LGD × EAD
```

Must show:

```text id="0n6xmn"
expected loss by applicant
expected loss by risk grade
expected loss by decision
base vs stressed loss
fraud loss
stablecoin risk exposure
```

Data source:

```text id="137p5p"
expected_loss_summary.json
expected_loss_by_segment.json
stress_loss_summary.json
```

---

## 11. Model Risk & Validation

Purpose:

```text id="lk4sgt"
Show whether models can be trusted for decisions.
```

Must show:

```text id="inyj8g"
credit calibration
PD decile default table
champion vs challenger comparison
fraud precision-recall tradeoff
score drift
PSI summary
segment weakness
model verdicts
```

Allowed verdicts:

```text id="qa3fu4"
Pass
Monitor
Fail
```

Data source:

```text id="8sg6j2"
model_validation_summary.json
champion_challenger_comparison.json
model_risk_verdicts.json
```

---

## 12. Stress Testing

Purpose:

```text id="z720nu"
Show loss sensitivity under worse conditions.
```

Required scenarios:

```text id="hhp2v5"
Base
Moderate Stress
Severe Stress
```

Must show:

```text id="9qf6xv"
PD stress impact
LGD stress impact
fraud loss impact
stablecoin risk impact
total expected loss impact
```

Do not claim macro causality unless explicitly modeled.

---

## 13. Evidence & Methodology

Purpose:

```text id="8qtgks"
Explain data, assumptions, validation, and limitations.
```

Must include:

```text id="wos431"
data sources
synthetic data disclosure
model list
split method
loss assumptions
stress assumptions
validation methods
known limitations
```

Data source:

```text id="e6gi23"
methodology_summary.json
data_quality_report.csv
```

---

## 14. Required Interaction Rules

Interactions must be limited to:

```text id="thkbo1"
policy sliders
threshold selectors
stress scenario selector
table row selection
module tabs
chart hover states
```

Do not add decorative 3D, games, chatbots, or unrelated animations.

---

## 15. Required Copy Rules

Use precise risk language.

Allowed:

```text id="0bk1s5"
estimated expected loss
modeled default probability
manual-review threshold
validation evidence
synthetic stablecoin sample
```

Forbidden:

```text id="b8i23m"
production-ready
institutional-grade
guaranteed fraud detection
AML compliance
optimal credit policy
AI-powered magic
```

---

## 16. Responsiveness

Primary target:

```text id="kbdmxt"
desktop and laptop
```

Secondary target:

```text id="9cj7id"
tablet
```

Mobile must be readable, but the project is desktop-first.

Do not sacrifice dashboard density for mobile aesthetics.

---

## 17. Performance Requirements

Frontend must:

```text id="f5u5m7"
load from static JSON
avoid heavy client computation
render tables efficiently
avoid unnecessary animation
keep charts readable
```

No backend server required for the portfolio version.

---

## 18. Build Boundary

Project root:

```text id="9fiamy"
/Users/vatsal/Documents/credits-lab
```

Docs path:

```text id="6cma07"
/Users/vatsal/Documents/credits-lab/docs
```

Do not create `README.md` unless explicitly requested by the user.

Do not invent metrics in the frontend.

Every number must trace to `data/outputs`.
