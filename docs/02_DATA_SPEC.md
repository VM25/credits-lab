# 02_DATA_SPEC.md

# Data Specification

## 1. Data Goal

Use data only to support four outputs:

```text id="bik3yd"
underwriting decisions
fraud / payments risk decisions
expected-loss estimates
model-risk validation
```

Do not add data that does not support these outputs.

---

## 2. Project Paths

Project root:

```text id="h03xo8"
/Users/vatsal/Documents/credits-lab
```

Docs path:

```text id="g40qan"
/Users/vatsal/Documents/credits-lab/docs
```

Expected data paths:

```text id="9xbfmn"
data/raw
data/interim
data/processed
data/outputs
```

Do not create `README.md` unless explicitly requested by the user.

---

## 3. Required Data Domains

The project needs four data domains:

```text id="sy79hr"
credit applicants / loans
card or payment transactions
stablecoin payment transactions
macro / stress variables
```

Keep each domain separate until final reporting.

---

## 4. Credit Underwriting Data

Purpose:

```text id="q9e6bp"
Estimate borrower default risk and support approve / review / decline decisions.
```

Acceptable source type:

* public consumer credit dataset
* accepted loan data
* rejected applicant data if available
* synthetic rejected applicants only if clearly labeled

Minimum fields:

```text id="zzsamh"
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

Required target:

```text id="t8pys5"
default_flag
```

Allowed engineered features:

```text id="2m7g6g"
income_to_loan_ratio
debt_burden_score
credit_utilization_band
loan_size_band
credit_grade_numeric
prior_delinquency_flag
application_vintage
```

Forbidden leakage fields:

```text id="zzthc4"
future payment status
recoveries after default
collections after default
final loan outcome fields unavailable at application
post-origination behavior for initial underwriting
```

---

## 5. Fraud / Payments Data

Purpose:

```text id="seel6u"
Score transaction risk and support approve / step-up / review / block decisions.
```

Acceptable source type:

* public card fraud dataset
* generated payment stream
* hybrid public + synthetic transaction data

Minimum fields:

```text id="1uc9rd"
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

Required target if supervised:

```text id="38n2e8"
fraud_flag
```

Allowed engineered features:

```text id="kk97o1"
velocity_1h
velocity_24h
amount_zscore_by_account
merchant_risk_score
new_device_flag
new_location_flag
night_transaction_flag
high_amount_flag
```

Fraud is imbalanced. Do not use accuracy as the main metric.

---

## 6. Stablecoin Payments Data

Purpose:

```text id="lyu9n1"
Show modern payments-risk monitoring without turning the project into a crypto project.
```

Allowed source type:

* synthetic stablecoin transaction data
* public blockchain-style transaction sample if simple to ingest
* generated wallet network

Minimum fields:

```text id="wpomwi"
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

Allowed engineered features:

```text id="3r9hpz"
wallet_velocity
inflow_outflow_ratio
counterparty_concentration
round_trip_proxy
large_transfer_flag
new_counterparty_flag
risk_exposure_score
```

Forbidden:

```text id="qocxs2"
token price prediction
DeFi yield data
NFT data
crypto trading signals
portfolio returns
```

---

## 7. Macro / Stress Data

Purpose:

```text id="gs9n3d"
Support stress testing and loss-sensitivity analysis.
```

Minimum fields:

```text id="e3spdd"
date
unemployment_rate
policy_rate
inflation_rate
consumer_credit_delinquency_rate
credit_card_chargeoff_rate
```

Use macro data only for:

```text id="2t7xzl"
stress scenarios
loss overlays
portfolio deterioration assumptions
```

Do not pretend macro variables caused individual defaults unless modeled and documented.

---

## 8. Data Splits

Use time-aware splits where dates exist.

Default split:

```text id="9cifhj"
train: earliest 70%
validation: next 15%
test: latest 15%
```

If no date exists:

```text id="gwss2c"
use stratified train / validation / test split
state limitation clearly
```

Never tune thresholds on the final test set.

---

## 9. Required Data Outputs

Processed outputs must include:

```text id="lykhfr"
processed_credit_applicants.csv
processed_payment_transactions.csv
processed_stablecoin_transactions.csv
macro_stress_inputs.csv
underwriting_model_dataset.csv
fraud_model_dataset.csv
validation_dataset.csv
```

Frontend-ready outputs must include:

```text id="67tj5m"
risk_command_center.json
underwriting_decisions.json
fraud_alerts.json
stablecoin_alerts.json
expected_loss_summary.json
model_validation_summary.json
policy_simulator_inputs.json
```

---

## 10. Data Quality Checks

Run and report:

```text id="rb03xc"
row count
column count
missing values
duplicate IDs
target distribution
date range
class imbalance
outlier summary
train/test leakage check
schema validation
```

Stop the build if target leakage is detected.

---

## 11. Assumption Rules

Clearly label:

```text id="lyzaa4"
public data
synthetic data
generated features
imputed values
stress assumptions
LGD assumptions
EAD assumptions
fraud-loss assumptions
```

Do not present synthetic data as observed history.

Do not present public sample data as proprietary bank data.

Do not overclaim real-time production use.

---

## 12. Final Data Standard

The data layer succeeds only if every dataset can answer one of these:

```text id="rj4t4s"
Who should receive credit?
Which transaction is suspicious?
How much loss is expected?
Can the model be trusted?
```

Delete or ignore data that does not support those questions.
