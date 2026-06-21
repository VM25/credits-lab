# 05_EXPECTED_LOSS_ENGINE_SPEC.md

# Expected Loss Engine Specification

## 1. Module Purpose

Build the loss translation layer.

It must answer:

```text id="n7ni22"
How much money could be lost under this credit or payment decision?
```

The module must convert model outputs into financial loss estimates.

This is the bridge between prediction and risk strategy.

---

## 2. Required Inputs

Credit inputs:

```text id="5psd4g"
applicant_id
PD
risk_grade
decision
recommended_credit_limit
loan_amount
annual_income
debt_to_income
```

Fraud inputs:

```text id="ybp0zn"
transaction_id
fraud_probability
fraud_score
transaction_amount
payment_action
```

Stablecoin inputs:

```text id="j3y3r7"
wallet_id
stablecoin_risk_score
amount_usd
stablecoin_risk_action
```

Macro / stress inputs:

```text id="tmcqhu"
unemployment_rate
policy_rate
inflation_rate
consumer_credit_delinquency_rate
credit_card_chargeoff_rate
```

---

## 3. Credit Expected Loss Formula

Use:

```text id="891i6q"
Expected Loss = PD × LGD × EAD
```

Definitions:

```text id="k76nfn"
PD = probability of default
LGD = loss given default
EAD = exposure at default
```

Required outputs:

```text id="ry6sa4"
PD
LGD
EAD
expected_loss
expected_loss_rate
```

---

## 4. LGD Assumptions

Default LGD assumptions:

```text id="w5lzkz"
secured / low-risk credit: 35%
standard consumer credit: 55%
high-risk unsecured credit: 75%
```

If no product type exists, use:

```text id="gh03lx"
LGD = 55%
```

LGD must be clearly labeled as an assumption.

Do not imply observed recovery modeling unless recovery data is used.

---

## 5. EAD Assumptions

For installment-style credit:

```text id="m1v8em"
EAD = loan_amount
```

For revolving credit:

```text id="g9yckm"
EAD = recommended_credit_limit × utilization_assumption
```

Default utilization assumption:

```text id="yyrlna"
utilization_assumption = 65%
```

EAD must be clearly labeled as estimated exposure.

---

## 6. Credit Decision Profitability

Calculate simple risk-adjusted value:

```text id="gwwy4y"
net_expected_value = expected_revenue - expected_loss
```

Allowed revenue proxy:

```text id="8f1evl"
expected_revenue = interest_rate × EAD
```

Do not claim full loan profitability.

Ignore servicing cost, funding cost, prepayment, and capital cost unless explicitly modeled.

---

## 7. Fraud Expected Loss Formula

Use:

```text id="c2xq1z"
Expected Fraud Loss = fraud_probability × transaction_amount × loss_severity
```

Default loss severity:

```text id="j4e7nr"
loss_severity = 90%
```

If `fraud_probability` is unavailable, use normalized fraud score and label it as a proxy.

Required outputs:

```text id="wbxukz"
fraud_probability
transaction_amount
loss_severity
expected_fraud_loss
```

---

## 8. Stablecoin Risk Loss Proxy

Use:

```text id="b00kx0"
Stablecoin Risk Exposure = stablecoin_risk_score × amount_usd
```

This is a risk exposure proxy, not realized loss.

Required outputs:

```text id="n0l0lm"
stablecoin_risk_score
amount_usd
stablecoin_risk_exposure
stablecoin_risk_action
```

Do not call this AML loss.

Do not claim compliance coverage.

---

## 9. Segment Loss Views

Aggregate expected loss by:

```text id="82imou"
risk_grade
decision
credit_grade
loan_purpose
income_band
debt_to_income_band
application_vintage
payment_action
merchant_risk_band
stablecoin_risk_action
```

Required outputs:

```text id="196c0k"
total_expected_loss
average_expected_loss
expected_loss_rate
account_count
exposure
```

---

## 10. Stress Scenarios

Create three stress cases.

### Base Case

```text id="ldxk16"
PD multiplier = 1.00
LGD multiplier = 1.00
fraud loss multiplier = 1.00
```

### Moderate Stress

```text id="ekqei4"
PD multiplier = 1.25
LGD multiplier = 1.10
fraud loss multiplier = 1.20
```

### Severe Stress

```text id="55qgrx"
PD multiplier = 1.60
LGD multiplier = 1.25
fraud loss multiplier = 1.50
```

Cap stressed PD at:

```text id="bkwaje"
100%
```

---

## 11. Policy Loss Comparison

For each policy threshold, report:

```text id="ly8d6t"
approval_rate
review_rate
decline_rate
approved_exposure
expected_credit_loss
expected_fraud_loss
stablecoin_risk_exposure
total_expected_loss
loss_rate
```

This supports the policy simulator.

Do not optimize only for lowest loss.

Show growth-risk tradeoff.

---

## 12. Required Outputs

Create:

```text id="f5x52y"
data/outputs/expected_loss_applicant_level.csv
data/outputs/expected_loss_summary.json
data/outputs/expected_loss_by_segment.json
data/outputs/stress_loss_summary.json
data/outputs/policy_loss_comparison.json
```

Each applicant row must include:

```text id="h36scp"
applicant_id
PD
LGD
EAD
expected_loss
expected_loss_rate
base_loss
moderate_stress_loss
severe_stress_loss
```

---

## 13. Required Charts

Generate frontend-ready data for:

```text id="wkgg8r"
expected loss by risk grade
expected loss by decision
expected loss waterfall
base vs stressed loss
approval rate vs expected loss
credit exposure vs loss rate
fraud loss by payment action
stablecoin risk exposure by action
policy threshold loss curve
```

No decorative charts.

---

## 14. Validation Rules

Check:

```text id="ng3tsk"
PD is between 0 and 1
LGD is between 0 and 1
EAD is non-negative
expected loss is non-negative
stressed PD is capped at 1
segment totals reconcile to portfolio total
```

Stop if totals do not reconcile.

---

## 15. Assumption Rules

Clearly label:

```text id="jwmxiq"
LGD assumptions
EAD assumptions
utilization assumptions
fraud severity assumptions
stress multipliers
stablecoin proxy methodology
```

Do not present assumption-driven losses as observed realized losses.

---

## 16. Build Boundary

Do not create `README.md` unless explicitly requested by the user.

Do not build frontend components from this doc alone.

This doc only defines expected-loss math, stress logic, outputs, and constraints.
