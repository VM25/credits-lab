# 04_FRAUD_PAYMENTS_RISK_SPEC.md

# Fraud & Payments Risk Specification

## 1. Module Purpose

Build the transaction-risk module.

It must answer:

```text id="zbp8vx"
Is this payment normal, suspicious, reviewable, or blockable?
```

The module must convert transaction data into:

```text id="uzzksr"
fraud risk score
anomaly flag
payment action
expected fraud loss
manual-review priority
stablecoin risk flag
```

This is not a standalone Kaggle fraud classifier.

---

## 2. Required Inputs

Use processed payment data from:

```text id="9w2c0m"
data/processed/processed_payment_transactions.csv
```

Use stablecoin data from:

```text id="zf7fvi"
data/processed/processed_stablecoin_transactions.csv
```

Do not mix card/payment and stablecoin data until reporting.

---

## 3. Card / Payment Transaction Fields

Required fields:

```text id="i1yfzw"
transaction_id
account_id
transaction_time
amount
merchant_category
merchant_risk_band
location_proxy
device_proxy
account_age_days
transaction_count_24h
amount_count_24h
fraud_flag
chargeback_loss
```

Allowed engineered fields:

```text id="wwzxyq"
velocity_1h
velocity_24h
amount_zscore_by_account
merchant_risk_score
new_device_flag
new_location_flag
night_transaction_flag
high_amount_flag
account_tenure_band
```

Do not use fields unavailable at transaction time.

---

## 4. Stablecoin Transaction Fields

Required fields:

```text id="s0xaws"
wallet_id
counterparty_wallet_id
transaction_time
token_type
amount_usd
wallet_age_days
inflow_24h
outflow_24h
transaction_count_24h
counterparty_risk_score
risky_address_exposure_flag
stablecoin_risk_label
```

Allowed engineered fields:

```text id="tvn9a5"
wallet_velocity
inflow_outflow_ratio
counterparty_concentration
round_trip_proxy
large_transfer_flag
new_counterparty_flag
risk_exposure_score
```

Stablecoin scope is payments risk only.

No crypto trading, DeFi, NFT, yield, or token-price logic.

---

## 5. Fraud Target

Primary target if labels exist:

```text id="kjhnof"
fraud_flag
```

Definition:

```text id="jra07d"
1 = fraudulent or charged-back transaction
0 = legitimate transaction
```

If labels are synthetic, label them clearly.

Do not present generated labels as observed fraud history.

---

## 6. Model Stack

Build three layers.

### A. Rules Engine

Required rules:

```text id="a9gomj"
high amount
high velocity
new device
new location
high-risk merchant
short account age
unusual account amount
```

Purpose:

```text id="mk8iyl"
transparent baseline controls
```

### B. Supervised Fraud Model

Use only if labels exist.

Allowed models:

```text id="t0f563"
logistic regression
gradient boosting
random forest
```

Required outputs:

```text id="sj3vf0"
fraud_probability
fraud_score
top_risk_drivers
```

Do not use accuracy as the main metric.

### C. Anomaly Model

Use for unlabeled or hybrid data.

Allowed models:

```text id="f6ohp9"
Isolation Forest
Local Outlier Factor
robust z-score rules
```

Required output:

```text id="iayl68"
anomaly_score
```

---

## 7. Payment Actions

Map fraud score to action.

Default policy:

```text id="s2rmte"
Approve: score < 0.35
Step-up verification: 0.35 ≤ score < 0.60
Manual review: 0.60 ≤ score < 0.80
Block: score ≥ 0.80
```

Thresholds must be configurable for the policy simulator.

Required output:

```text id="dpmsd5"
payment_action
```

---

## 8. Stablecoin Risk Actions

Map stablecoin risk score to action.

Default policy:

```text id="lnodr2"
Normal: score < 0.40
Monitor: 0.40 ≤ score < 0.65
Review: 0.65 ≤ score < 0.85
High-risk wallet: score ≥ 0.85
```

Required output:

```text id="pfy7zk"
stablecoin_risk_action
```

Do not claim AML compliance.

Use the phrase:

```text id="8q3q24"
AML-style risk indicators
```

not:

```text id="8i89ly"
AML compliance system
```

---

## 9. Expected Fraud Loss

Calculate:

```text id="hxvb9j"
Expected Fraud Loss = fraud_probability × transaction_amount × loss_severity
```

If fraud probability is unavailable, use normalized risk score with clear labeling.

Required fields:

```text id="q1uowo"
fraud_probability
transaction_amount
loss_severity
expected_fraud_loss
```

Loss severity assumption must be documented.

---

## 10. Manual Review Queue

Create ranked queue.

Priority logic must consider:

```text id="won83m"
fraud score
transaction amount
expected fraud loss
risk drivers
review capacity
```

Required output:

```text id="zattbb"
manual_review_priority
```

Do not send every high-score item to review if review capacity is exceeded.

---

## 11. Required Metrics

Fraud is imbalanced.

Primary metrics:

```text id="w8pdef"
PR-AUC
precision
recall
fraud capture rate
false-positive rate
false-negative rate
expected fraud loss avoided
manual-review volume
```

Secondary metrics:

```text id="kjuuvj"
ROC-AUC
confusion matrix
score distribution
```

Accuracy is not acceptable as the main performance metric.

---

## 12. Cost Tradeoff

Report cost by threshold.

Required costs:

```text id="kbync2"
false positive cost
false negative cost
manual review cost
blocked legitimate payment cost
fraud loss cost
```

Required chart data:

```text id="ez3ggd"
threshold vs fraud captured
threshold vs false positives
threshold vs review volume
threshold vs expected fraud loss
```

---

## 13. Required Outputs

Create:

```text id="pr4jcl"
data/outputs/fraud_alerts.csv
data/outputs/fraud_alerts.json
data/outputs/stablecoin_alerts.csv
data/outputs/stablecoin_alerts.json
data/outputs/fraud_policy_summary.json
```

Each transaction row must include:

```text id="9vo2cx"
transaction_id
account_id
transaction_time
amount
fraud_score
anomaly_score
payment_action
expected_fraud_loss
top_reason_1
top_reason_2
top_reason_3
manual_review_priority
```

Each stablecoin row must include:

```text id="0qwpyv"
wallet_id
counterparty_wallet_id
transaction_time
amount_usd
stablecoin_risk_score
stablecoin_risk_action
risk_exposure_score
top_reason_1
top_reason_2
top_reason_3
```

---

## 14. Required Charts

Generate frontend-ready data for:

```text id="j7autb"
fraud score distribution
payment action mix
fraud capture vs threshold
false positives vs threshold
manual review volume vs threshold
expected fraud loss by action
top fraud reason-code frequency
stablecoin risk score distribution
stablecoin action mix
wallet risk leaderboard
```

No decorative cybersecurity charts.

---

## 15. Leakage Rules

Forbidden fields:

```text id="7toh53"
chargeback outcome before transaction decision
future account behavior
post-investigation fraud result
manual review result before scoring
future merchant fraud rate
future wallet risk label
```

If leakage is detected, stop and fix the dataset.

Do not continue with contaminated results.

---

## 16. Build Boundary

Do not create `README.md` unless explicitly requested by the user.

Do not build frontend components from this doc alone.

This doc only defines fraud, payments, stablecoin-risk logic, outputs, and constraints.
