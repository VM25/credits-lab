# 08_OUTPUTS_AND_REPORTING_SPEC.md

# Outputs and Reporting Specification

## 1. Purpose

Define all final engine outputs.

Every output must support one of four questions:

```text id="uxbi2h"
Who receives credit?
Which payments are risky?
How much loss is expected?
Can the models be trusted?
```

Do not create unused reports.

---

## 2. Output Directory

All final outputs must be written to:

```text id="8k9k5c"
data/outputs
```

Do not create `README.md` unless explicitly requested by the user.

---

## 3. Required CSV Outputs

Create:

```text id="7zjk7u"
underwriting_decisions.csv
fraud_alerts.csv
stablecoin_alerts.csv
expected_loss_applicant_level.csv
credit_model_validation.csv
fraud_model_validation.csv
stablecoin_model_validation.csv
policy_threshold_grid.csv
data_quality_report.csv
```

CSV files are for auditability and tabular review.

---

## 4. Required JSON Outputs

Create:

```text id="4i2916"
risk_command_center.json
underwriting_decisions.json
underwriting_policy_summary.json
fraud_alerts.json
stablecoin_alerts.json
fraud_policy_summary.json
expected_loss_summary.json
expected_loss_by_segment.json
stress_loss_summary.json
policy_loss_comparison.json
policy_simulator_inputs.json
policy_simulator_results.json
model_validation_summary.json
champion_challenger_comparison.json
model_risk_verdicts.json
methodology_summary.json
```

JSON files are for frontend use.

---

## 5. Risk Command Center Output

File:

```text id="pqir7l"
risk_command_center.json
```

Must include:

```text id="v0xicg"
total_applicants
approval_rate
review_rate
decline_rate
average_PD
total_approved_exposure
total_expected_credit_loss
total_expected_fraud_loss
stablecoin_risk_exposure
manual_review_volume
model_verdict_summary
highest_risk_segment
```

This is the dashboard summary.

---

## 6. Underwriting Report

Files:

```text id="tw0fe9"
underwriting_decisions.csv
underwriting_decisions.json
underwriting_policy_summary.json
```

Must include:

```text id="7y2jfb"
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

Required summary:

```text id="kh0hod"
approval mix
risk-grade mix
average PD by decision
expected loss by decision
top decline reasons
```

---

## 7. Fraud / Payments Report

Files:

```text id="xcmnv7"
fraud_alerts.csv
fraud_alerts.json
fraud_policy_summary.json
```

Must include:

```text id="ssmy0t"
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

Required summary:

```text id="6i8d1y"
payment action mix
fraud score distribution
expected fraud loss by action
manual-review queue size
top fraud drivers
```

---

## 8. Stablecoin Risk Report

Files:

```text id="g03x29"
stablecoin_alerts.csv
stablecoin_alerts.json
```

Must include:

```text id="54fttq"
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

Required summary:

```text id="8gmn1n"
stablecoin action mix
high-risk wallet count
risk exposure by action
top wallet-risk drivers
```

Use “AML-style risk indicators,” not “AML compliance.”

---

## 9. Expected Loss Report

Files:

```text id="1ft4ku"
expected_loss_applicant_level.csv
expected_loss_summary.json
expected_loss_by_segment.json
stress_loss_summary.json
policy_loss_comparison.json
```

Must include:

```text id="m2yk8a"
base_expected_loss
moderate_stress_loss
severe_stress_loss
expected_loss_by_risk_grade
expected_loss_by_decision
expected_loss_by_segment
approval_rate_vs_loss
```

All LGD, EAD, severity, and stress assumptions must be labeled.

---

## 10. Model Validation Report

Files:

```text id="nuxp7y"
model_validation_summary.json
credit_model_validation.csv
fraud_model_validation.csv
stablecoin_model_validation.csv
champion_challenger_comparison.json
model_risk_verdicts.json
```

Must include:

```text id="ig0dcw"
model_name
model_type
primary_metric
calibration_status
stability_status
segment_status
explainability_status
validation_verdict
verdict_reason
```

Allowed verdicts:

```text id="yvcaqi"
Pass
Monitor
Fail
```

Every verdict needs one sentence of evidence.

---

## 11. Data Quality Report

File:

```text id="ny2x1s"
data_quality_report.csv
```

Must include:

```text id="ci1f99"
dataset_name
row_count
column_count
missing_value_count
duplicate_id_count
target_rate
date_min
date_max
leakage_check_status
schema_check_status
```

Stop if leakage status is failed.

---

## 12. Methodology Summary

File:

```text id="6rg8qu"
methodology_summary.json
```

Must include:

```text id="22rmr3"
data_sources
synthetic_data_disclosure
model_list
feature_summary
split_method
loss_assumptions
stress_assumptions
validation_methods
known_limitations
```

Do not overstate the project.

---

## 13. Frontend Chart Data

Generate chart-ready JSON for:

```text id="xkvo3m"
PD distribution
risk-grade distribution
approval mix
approval rate vs expected loss
fraud score distribution
payment action mix
fraud threshold tradeoff
stablecoin risk distribution
expected loss waterfall
base vs stressed loss
calibration curve
model verdict panel
segment performance heatmap
```

No decorative charts.

---

## 14. Reporting Language Rules

Allowed language:

```text id="t4sbja"
estimated expected loss
modeled default probability
simulated stress case
synthetic stablecoin transaction sample
model validation evidence
```

Forbidden language:

```text id="nt7xcg"
production-ready system
institutional-grade model
real-time bank deployment
AML compliance platform
guaranteed fraud detection
optimal credit policy
```

---

## 15. Reconciliation Rules

Before final export, verify:

```text id="rmehbj"
applicant totals reconcile
transaction totals reconcile
segment totals reconcile
expected loss totals reconcile
policy simulator totals reconcile
validation verdicts match validation metrics
```

Stop if totals do not reconcile.

---

## 16. Final Standard

The output layer succeeds only if every frontend number can be traced to a backend CSV or JSON file.

No hardcoded frontend metrics.

No unsupported claims.
