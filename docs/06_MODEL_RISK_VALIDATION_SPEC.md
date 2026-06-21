# 06_MODEL_RISK_VALIDATION_SPEC.md

# Model Risk & Validation Specification

## 1. Module Purpose

Build the model validation layer.

It must answer:

```text id="x6m8ta"
Can these models be trusted for credit and payments risk decisions?
```

Validation is a core module.

It is not an appendix.

---

## 2. Models to Validate

Validate:

```text id="k7ih3q"
underwriting champion model
underwriting challenger model
fraud supervised model
fraud anomaly model
stablecoin risk scoring model
```

If a model is rule-based, validate rule behavior and threshold impact.

---

## 3. Validation Categories

Each model must be tested across:

```text id="j0f8ob"
performance
calibration
stability
drift
segment behavior
threshold behavior
explainability
decision usefulness
```

Do not report model accuracy alone.

---

## 4. Credit Model Metrics

Required credit metrics:

```text id="q8em3r"
ROC-AUC
PR-AUC
Brier score
KS statistic
confusion matrix
calibration curve
decile default table
approval-rate / loss-rate tradeoff
```

Required validation views:

```text id="lk2lm9"
predicted PD vs actual default
default rate by PD decile
expected loss by risk grade
approval decision by risk grade
champion vs challenger comparison
```

---

## 5. Fraud Model Metrics

Required fraud metrics:

```text id="ui2v2f"
PR-AUC
precision
recall
fraud capture rate
false-positive rate
false-negative rate
manual-review volume
expected fraud loss avoided
```

Secondary metrics:

```text id="sjmkzn"
ROC-AUC
confusion matrix
score distribution
```

Accuracy is forbidden as the headline fraud metric.

---

## 6. Stablecoin Risk Validation

Validate stablecoin module as a risk scoring system.

Required checks:

```text id="lr6625"
score distribution
risk action mix
high-risk wallet concentration
risky exposure by score band
threshold sensitivity
top risk-driver frequency
```

Do not claim AML compliance.

Use:

```text id="7s7fkc"
AML-style risk indicators
```

Do not use:

```text id="i0spxo"
AML compliance system
```

---

## 7. Calibration Tests

Credit PD models must be calibrated.

Required outputs:

```text id="2p47pg"
calibration_curve.json
decile_default_table.csv
brier_score
predicted_vs_actual_default_by_band
```

Validation rule:

```text id="99b0zz"
If predicted risk does not broadly match observed default by band, flag calibration weakness.
```

Do not use uncalibrated model scores for expected loss without disclosure.

---

## 8. Stability and Drift

Run stability checks across time or split periods.

Required checks:

```text id="bjni9c"
train vs test score distribution
feature distribution shift
target rate shift
population stability index
performance by vintage
model score drift
```

Default PSI interpretation:

```text id="r7fpyu"
PSI < 0.10: stable
0.10 ≤ PSI < 0.25: monitor
PSI ≥ 0.25: material shift
```

Do not overstate PSI as a regulatory standard.

---

## 9. Segment-Level Validation

Test performance by:

```text id="39vcsk"
credit grade
income band
debt-to-income band
loan purpose
risk grade
application vintage
merchant risk band
payment action
stablecoin risk action
```

Required outputs:

```text id="j22c7s"
segment_count
event_rate
average_score
model_metric_by_segment
expected_loss_by_segment
decision_rate_by_segment
```

Flag weak segments.

Do not hide poor segment performance behind strong overall metrics.

---

## 10. Explainability

Required explainability outputs:

```text id="kubqad"
feature importance
reason-code frequency
top drivers by decision
top drivers by risk grade
example applicant explanation
example transaction explanation
```

Allowed methods:

```text id="l734ee"
logistic coefficients
tree feature importance
permutation importance
SHAP if available
rule-trigger summaries
```

Do not use vague explanations.

Forbidden reason codes:

```text id="h0qm0s"
AI says risky
complex model pattern
unknown model reason
black-box decision
```

---

## 11. Champion vs Challenger

Compare underwriting models.

Champion:

```text id="p9hn6r"
logistic regression scorecard
```

Challenger:

```text id="wb8v5o"
gradient boosting model
```

Required comparison:

```text id="k5e353"
ROC-AUC
PR-AUC
Brier score
calibration quality
expected loss separation
explainability
stability
segment weakness
```

Do not automatically choose the highest-AUC model.

Final model choice must consider explainability and calibration.

---

## 12. Threshold Validation

Validate policy thresholds.

Required views:

```text id="z9s2e5"
approval threshold vs approval rate
approval threshold vs expected loss
fraud threshold vs fraud captured
fraud threshold vs false positives
fraud threshold vs review volume
stablecoin threshold vs risky exposure
```

Thresholds must support business tradeoff discussion.

Do not present one threshold as objectively optimal without constraints.

---

## 13. Validation Verdicts

Each model receives one verdict:

```text id="f72ym8"
Pass
Monitor
Fail
```

Verdict rules:

### Pass

```text id="q5la4q"
acceptable performance, calibration, stability, and explainability
```

### Monitor

```text id="lbzd9u"
usable with clear weakness or drift risk
```

### Fail

```text id="s0g5zk"
not reliable for decision use
```

Explain every verdict in one sentence.

---

## 14. Required Outputs

Create:

```text id="k7ou4m"
data/outputs/model_validation_summary.json
data/outputs/credit_model_validation.csv
data/outputs/fraud_model_validation.csv
data/outputs/stablecoin_model_validation.csv
data/outputs/champion_challenger_comparison.json
data/outputs/model_risk_verdicts.json
```

Each verdict row must include:

```text id="xuffcf"
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

---

## 15. Required Charts

Generate frontend-ready data for:

```text id="97ddjo"
credit calibration curve
PD decile default table
champion vs challenger comparison
score drift chart
PSI summary
segment performance heatmap
fraud precision-recall curve
fraud threshold tradeoff
stablecoin risk distribution
model verdict panel
```

No decorative model charts.

---

## 16. Stop Conditions

Stop and fix before reporting if:

```text id="a4nb6i"
target leakage is detected
test metrics are missing
calibration cannot be measured
fraud class imbalance is ignored
expected loss inputs do not reconcile
model output cannot be explained
synthetic labels are not disclosed
```

Do not continue with contaminated validation.

---

## 17. Build Boundary

Do not create `README.md` unless explicitly requested by the user.

Do not build frontend components from this doc alone.

This doc only defines validation logic, outputs, verdicts, and constraints.
