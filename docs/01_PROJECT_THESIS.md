# 01_PROJECT_THESIS.md

# Project Thesis

## 1. Core Idea

Credit and payments risk is not a pure prediction problem.

The real problem is decision control:

```text
Who should be approved?
Who should be reviewed?
Who should be declined?
Which payments are suspicious?
How much loss is expected?
Can the model be trusted?
```

This project builds a risk decision engine that connects model scores to underwriting, fraud controls, expected loss, and model validation.

---

## 2. Why This Project Exists

Most student projects stop at:

```text
Train model → report accuracy → show chart
```

That is not enough for credit, fraud, or payments risk.

A useful risk system must show:

* decision thresholds
* approval tradeoffs
* fraud alert tradeoffs
* expected loss
* review capacity
* model calibration
* drift
* explainability
* validation evidence

The project must prove that risk modeling is useful only when it becomes a controlled decision process.

---

## 3. Business Problem

A lender or payments company must grow without taking uncontrolled losses.

Approving too many applicants increases defaults.

Declining too many applicants rejects good customers.

Blocking too many payments hurts users.

Blocking too few payments increases fraud and chargebacks.

The project targets this tradeoff.

---

## 4. System Thesis

The system should answer four questions:

### 1. Underwriting

```text
Should this applicant receive credit?
```

### 2. Fraud / Payments

```text
Is this transaction suspicious?
```

### 3. Expected Loss

```text
How much money could be lost?
```

### 4. Model Risk

```text
Can the model be trusted for decisions?
```

Every module must map back to one of these questions.

---

## 5. Quant Thesis

The quant value is not model complexity.

The quant value is disciplined risk translation:

* probability of default
* loss given default
* exposure at default
* expected loss
* calibrated classification
* imbalanced fraud detection
* anomaly scoring
* threshold optimization
* stress testing
* drift monitoring
* model validation

The project must prefer clean, explainable risk logic over unnecessary model sophistication.

---

## 6. Stablecoin Thesis

Stablecoin payments are included only as a transaction-risk extension.

The purpose is to show modern payments-risk thinking:

* wallet-risk scoring
* transaction velocity
* suspicious transfer behavior
* risky counterparty exposure
* stablecoin payment anomaly detection

This is not a crypto investing project.

No token-price prediction.
No DeFi yield.
No NFT analytics.
No speculative blockchain dashboard.

---

## 7. Model Risk Thesis

A model can be dangerous even if it performs well in-sample.

The project must validate whether models are:

* accurate
* calibrated
* stable
* explainable
* segment-consistent
* resistant to drift
* usable under policy constraints

Model validation is a core pillar, not an appendix.

---

## 8. Final Project Claim

The final project must support this claim:

> I built a credit and payments risk decision engine that translates borrower and transaction data into underwriting decisions, fraud controls, expected-loss estimates, and model-risk validation evidence.

Do not make broader claims.

Do not claim production readiness.

Do not claim real-time institutional deployment.

---

## 9. Build Boundary

Project root:

```text
/Users/vatsal/Documents/credits-lab
```

Builder docs location:

```text
/Users/vatsal/Documents/credits-lab/docs
```

All project direction must follow the docs inside `docs`.

Do not create `README.md` unless explicitly requested by the user.

---

## 10. Success Standard

The project succeeds only if an interviewer can clearly see:

```text
This candidate understands how credit, fraud, payments, expected loss, and model validation connect inside a real risk decision workflow.
```
