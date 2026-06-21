# 00_PROJECT_SCOPE.md

# Credit & Payments Risk Decision Engine

## Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk

## 1. Purpose

Build a focused risk decision system for consumer credit and payments risk.

The project must show how borrower, account, transaction, and model-output data become real risk decisions:

* approve, review, or decline credit applicants
* assign risk bands and credit-limit recommendations
* flag suspicious payments
* estimate expected credit and fraud losses
* validate whether models are stable, calibrated, explainable, and usable

This is a decision engine, not a generic prediction notebook.

---

## 2. Core Thesis

Credit and payments risk is not only a machine-learning problem.

A useful risk system must convert model scores into controlled decisions under loss, fraud, fairness, explainability, drift, and operational-review constraints.

---

## 3. Target Roles

This project is built for:

* Credit Risk Analyst
* Credit Strategy Analyst
* Fraud Risk Analyst
* Payments Risk Analyst
* Underwriting Strategy Analyst
* Risk Data Scientist
* Lending Strategy Analyst
* Transaction Risk Analyst
* Credit Model Validation / Model Risk roles

---

## 4. Main Modules

### A. Underwriting Strategy

Estimate borrower default risk and convert it into credit decisions.

Required outputs:

* probability of default
* risk grade
* approve / review / decline decision
* credit-limit recommendation
* adverse-action reason codes
* approval and loss tradeoff

---

### B. Fraud & Payments Risk

Score transaction-level risk and identify suspicious activity.

Required outputs:

* transaction risk score
* fraud/anomaly flag
* approve / step-up / review / block action
* false-positive and false-negative cost view
* manual-review volume

---

### C. Expected Loss Engine

Translate risk into financial loss estimates.

Required formula:

```text
Expected Loss = PD × LGD × EAD
```

Required outputs:

* expected loss per applicant
* expected loss by risk grade
* expected fraud/chargeback loss
* loss under policy changes
* loss under stress scenarios

---

### D. Model Risk & Validation

Test whether the models are reliable enough for decision use.

Required outputs:

* calibration results
* ROC-AUC / PR-AUC / Brier score
* drift and stability checks
* segment-level performance
* champion vs challenger comparison
* explainability and reason-code review
* validation verdict

---

### E. Stablecoin Payments Risk Module

Include only as a payments-risk extension.

Allowed scope:

* wallet-risk scoring
* transaction velocity
* suspicious flow behavior
* risky counterparty exposure
* stablecoin transaction anomaly detection

Forbidden scope:

* crypto trading
* token price prediction
* DeFi yield
* NFT analytics
* speculative blockchain dashboard

---

## 5. What This Project Is Not

This project is not:

* a Kaggle fraud classifier
* a default-prediction notebook
* a crypto project
* a full banking simulator
* a portfolio allocation project
* a marketing landing page
* a black-box AI demo
* a generic fintech dashboard

Every section must connect to risk decisioning, expected loss, fraud control, or model validation.

---

## 6. Required Final Deliverables

The final project must include:

* reproducible Python risk engine
* cleaned dataset outputs
* underwriting model
* fraud/payments risk model
* expected-loss engine
* model-validation report
* policy simulator data
* frontend dashboard
* README
* GitHub About description
* resume-ready project bullets

---

## 7. Frontend Requirement

The app must feel like a risk decision terminal.

Required sections:

1. Project overview
2. Risk command center
3. Underwriting decision engine
4. Policy simulator
5. Fraud and payments monitor
6. Stablecoin transaction-risk module
7. Expected-loss engine
8. Model-risk validation
9. Stress testing
10. Evidence and methodology

No decorative filler sections.

---

## 8. Success Criteria

The project is successful only if it demonstrates:

* credit-risk modeling
* transaction-risk monitoring
* expected-loss logic
* policy-threshold tradeoffs
* model validation
* explainable decisions
* realistic risk controls
* clean quant-finance positioning

The final story must be:

> I built a credit and payments risk decision framework that turns borrower and transaction data into underwriting decisions, fraud controls, expected-loss estimates, and model-risk validation evidence.

---

## 9. Non-Negotiable Constraints

* Use time-aware splits where applicable.
* Prevent target leakage.
* Report calibration, not just accuracy.
* Treat fraud as an imbalanced classification problem.
* Show cost tradeoffs, not only model metrics.
* Keep stablecoin risk secondary.
* Keep UI tied to real outputs.
* Clearly label assumptions and synthetic data.
* Do not overclaim production readiness.
* Do not present simulated values as real historical facts.
