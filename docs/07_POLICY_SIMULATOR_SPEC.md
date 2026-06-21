# 07_POLICY_SIMULATOR_SPEC.md

# Policy Simulator Specification

## 1. Module Purpose

Build the interactive policy simulator.

It must answer:

```text id="yqo2kq"
What happens if risk thresholds change?
```

The simulator must show tradeoffs between:

```text id="93v147"
growth
loss
fraud control
manual-review volume
model-risk exposure
```

This is not a decorative slider section.

---

## 2. Required Inputs

Use outputs from:

```text id="ssvx0k"
underwriting_decisions.json
fraud_alerts.json
stablecoin_alerts.json
expected_loss_summary.json
model_validation_summary.json
policy_loss_comparison.json
```

Do not create simulator values disconnected from backend outputs.

---

## 3. Credit Policy Controls

Required controls:

```text id="0bhlzw"
approval PD cutoff
manual-review PD band
decline PD cutoff
maximum expected-loss rate
minimum risk grade allowed
credit-limit multiplier
```

Default values:

```text id="8r0fy0"
Approve: PD < 6%
Review: 6% ≤ PD < 12%
Decline: PD ≥ 12%
credit-limit multiplier = 1.00
```

---

## 4. Fraud Policy Controls

Required controls:

```text id="em0ou1"
fraud approve threshold
step-up threshold
manual-review threshold
block threshold
manual-review capacity
fraud loss severity
```

Default values:

```text id="qau72g"
Approve: score < 0.35
Step-up: 0.35 ≤ score < 0.60
Review: 0.60 ≤ score < 0.80
Block: score ≥ 0.80
```

---

## 5. Stablecoin Policy Controls

Required controls:

```text id="8bbjig"
stablecoin monitor threshold
stablecoin review threshold
high-risk wallet threshold
risky counterparty tolerance
wallet velocity tolerance
```

Default values:

```text id="86jdl8"
Normal: score < 0.40
Monitor: 0.40 ≤ score < 0.65
Review: 0.65 ≤ score < 0.85
High-risk wallet: score ≥ 0.85
```

Use stablecoin controls only for payments-risk monitoring.

Do not imply AML compliance.

---

## 6. Stress Controls

Required controls:

```text id="acq33e"
PD stress multiplier
LGD stress multiplier
fraud loss multiplier
stablecoin risk multiplier
```

Default presets:

```text id="5vllxq"
Base
Moderate Stress
Severe Stress
```

Use multipliers from `05_EXPECTED_LOSS_ENGINE_SPEC.md`.

---

## 7. Simulator Outputs

Every control change must update:

```text id="t3ocrb"
approval rate
review rate
decline rate
approved exposure
expected credit loss
expected fraud loss
stablecoin risk exposure
total expected loss
loss rate
manual-review volume
blocked transaction rate
model-risk warnings
```

Do not update visuals without updating numbers.

---

## 8. Required Tradeoff Views

The simulator must show:

```text id="987kru"
approval rate vs expected loss
PD cutoff vs loss rate
fraud threshold vs fraud captured
fraud threshold vs false positives
manual-review volume vs capacity
stablecoin threshold vs risky exposure
stress severity vs total expected loss
```

No decorative charts.

---

## 9. Model-Risk Warnings

Trigger warnings when:

```text id="4hpwm8"
policy uses uncalibrated PD
threshold creates excessive review volume
segment loss rate becomes concentrated
fraud false positives increase sharply
stablecoin high-risk exposure increases
model validation verdict is Monitor or Fail
```

Warnings must be specific.

Forbidden warning:

```text id="lv8eld"
Risk is high.
```

Required warning style:

```text id="72kif3"
Manual review volume exceeds capacity by 18%.
```

---

## 10. Constraint Rules

The simulator must enforce:

```text id="rkr13g"
approve cutoff < review cutoff < decline cutoff
fraud approve threshold < step-up threshold < review threshold < block threshold
stablecoin monitor threshold < review threshold < high-risk threshold
PD between 0 and 1
LGD between 0 and 1
loss multipliers greater than 0
manual-review capacity non-negative
```

Reject invalid configurations.

---

## 11. Required Outputs

Create:

```text id="x7bpqh"
data/outputs/policy_simulator_inputs.json
data/outputs/policy_simulator_results.json
data/outputs/policy_threshold_grid.csv
```

Each scenario row must include:

```text id="rnxwlc"
scenario_id
credit_pd_cutoff
fraud_threshold
stablecoin_threshold
approval_rate
review_rate
decline_rate
expected_credit_loss
expected_fraud_loss
stablecoin_risk_exposure
total_expected_loss
manual_review_volume
model_risk_flag
```

---

## 12. Frontend Behavior

The frontend must let users adjust controls and immediately see:

```text id="vt1sbj"
decision mix
loss impact
review burden
fraud impact
stablecoin risk impact
model-risk warnings
```

The simulator must feel like a risk policy lab.

Not a generic dashboard filter.

---

## 13. Interpretation Rules

Do not present one setting as universally best.

Show tradeoffs.

Allowed language:

```text id="9lyf4s"
This policy reduces expected loss but lowers approval volume.
```

Forbidden language:

```text id="jvn1g3"
This is the optimal credit policy.
```

unless an explicit optimization constraint is defined.

---

## 14. Build Boundary

Do not create `README.md` unless explicitly requested by the user.

Do not build final frontend components from this doc alone.

This doc only defines simulator logic, controls, outputs, and constraints.
