# Backend & Data Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible Python risk engine that turns hybrid borrower/transaction data into a complete, reconciled `data/outputs` (9 CSV + 16 JSON) proving underwriting decisions, fraud controls, expected-loss estimates, and model-risk validation evidence.

**Architecture:** Modular `src/` package (data → models → risk → validation → reporting) driven by one orchestrator `src/run_pipeline.py`. Each module has one responsibility and writes deterministic outputs. Hybrid data: real LendingClub (credit), real Kaggle fraud labels + synthetic labeled context (payments), synthetic stablecoin, real FRED macro. Hard gates (leakage, reconciliation, required-output, determinism) fail the build.

**Tech Stack:** Python 3.9, pandas, numpy, scipy, scikit-learn, joblib, requests, kaggle; pytest for contract/range/reconciliation tests.

**Authority:** `docs/00…11` are source of truth; `docs/superpowers/specs/2026-06-20-credit-payments-risk-engine-design.md` operationalizes them. Exact field-by-field column mappings come from spec §5 and docs 02–08. Code blocks below give the contract-critical exact parts (constants, formulas, output schemas, test assertions); mechanical mapping follows the spec/docs precisely.

**Conventions:**
- All thresholds/assumptions/paths/seed come from `src/config.py` — never hardcode them elsewhere.
- All money/rate floats rounded at write time (6 dp) via `reporting/writers.py`.
- Outputs are deterministic: fixed seed, pinned `random_state`, sorted rows/keys.
- Raw downloads cached in `data/raw/` (gitignored); re-runs must not re-download if cache present.
- No `README.md`. No output files beyond the canonical 25 (+7 processed). Chart data embedded in required JSON.

---

## File Structure

```
requirements.txt                 # add scikit-learn, joblib, requests, kaggle; pytest (dev)
pytest.ini                       # test config
src/__init__.py
src/config.py                    # paths, SEED, thresholds, LGD/EAD/severity/stress, FRED series
src/run_pipeline.py              # orchestrator (phases in order; fail-fast)
src/data/__init__.py
src/data/ingest_macro.py         # FRED CSV pulls -> macro_stress_inputs.csv
src/data/ingest_credit.py        # LendingClub download+stratified sample+clean+leakage -> processed_credit_applicants.csv
src/data/ingest_payments.py      # Kaggle fraud + synthetic context -> processed_payment_transactions.csv
src/data/ingest_stablecoin.py    # synthetic -> processed_stablecoin_transactions.csv
src/data/features.py             # engineered features + model datasets + validation_dataset
src/data/splits.py               # time-aware 70/15/15
src/data/quality.py              # data_quality_report.csv + leakage check + schema validation
src/models/__init__.py
src/models/scorecard.py          # logistic-regression champion
src/models/gbm.py                # gradient-boosting challenger
src/models/calibration.py        # PD calibration + Brier + curve
src/models/anomaly.py            # IsolationForest / LOF
src/models/metrics.py            # ROC-AUC, PR-AUC, Brier, KS, confusion, PSI
src/risk/__init__.py
src/risk/underwriting.py         # PD->grade->decision->limit->reason codes
src/risk/fraud.py                # rules+supervised+anomaly->score->action->queue
src/risk/stablecoin.py           # wallet-risk scoring->action
src/risk/expected_loss.py        # EL + fraud loss + stablecoin exposure + segments + stress
src/risk/policy_simulator.py     # threshold grid + scenarios + constraints + warnings
src/validation/__init__.py
src/validation/validate.py       # metrics+calibration+drift+segments+champion/challenger+verdicts
src/reporting/__init__.py
src/reporting/writers.py         # deterministic CSV/JSON writers
src/reporting/command_center.py  # risk_command_center.json
src/reporting/methodology.py     # methodology_summary.json
src/reporting/reconcile.py       # reconciliation gate + required-output check
tests/                           # pytest contract/range/reconciliation/determinism tests
```

---

## Phase 1 — Repository setup

### Task 1.1: Clean prior build, create skeleton, requirements, pytest

**Files:**
- Delete: `src/build_backend.py`, `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/dist/`, `data/raw/*`, `data/processed/*`, `data/outputs/*` (prior synthetic build — "keep nothing")
- Create: module dirs + `__init__.py` per File Structure; `pytest.ini`
- Modify: `requirements.txt`

- [ ] **Step 1: Remove prior build artifacts**
```bash
cd /Users/vatsal/Documents/credits-lab
git rm -r --quiet src/build_backend.py frontend/dist data/processed data/outputs 2>/dev/null || true
rm -rf data/raw/* data/interim/* 2>/dev/null || true
# keep empty data dirs
mkdir -p data/raw data/interim data/processed data/outputs
```

- [ ] **Step 2: Create module skeleton**
```bash
mkdir -p src/data src/models src/risk src/validation src/reporting tests
for d in src src/data src/models src/risk src/validation src/reporting; do touch "$d/__init__.py"; done
touch tests/__init__.py
```

- [ ] **Step 3: Write `requirements.txt`**
```
pandas
numpy
scipy
scikit-learn
joblib
requests
kaggle
pytest
```

- [ ] **Step 4: Install deps**
Run: `python3 -m pip install --user -q -r requirements.txt`
Expected: completes; `python3 -c "import sklearn, joblib, kaggle; print('ok')"` prints `ok`

- [ ] **Step 5: Write `pytest.ini`**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
filterwarnings =
    ignore::DeprecationWarning
    ignore::UserWarning
```

- [ ] **Step 6: Commit**
```bash
git add -A
git commit -m "chore: remove prior build, scaffold modular src/ + pytest"
```

### Task 1.2: `src/config.py` — single source of constants

**Files:** Create `src/config.py`; Test `tests/test_config.py`

- [ ] **Step 1: Write failing test**
```python
# tests/test_config.py
from src import config

def test_thresholds_ordered_and_in_range():
    assert 0 < config.PD_APPROVE < config.PD_DECLINE < 1
    assert config.PD_APPROVE == 0.06 and config.PD_DECLINE == 0.12
    f = config.FRAUD_THRESHOLDS
    assert f["approve"] < f["stepup"] < f["review"] < f["block"]
    s = config.STABLECOIN_THRESHOLDS
    assert s["monitor"] < s["review"] < s["high_risk"]

def test_assumptions_present():
    assert config.LGD_DEFAULT == 0.55
    assert set(config.LGD_BY_RISK) >= {"low", "standard", "high"}
    assert config.UTILIZATION_ASSUMPTION == 0.65
    assert config.FRAUD_LOSS_SEVERITY == 0.90
    assert config.STRESS["severe"]["pd_mult"] == 1.60
    assert config.SEED == 20260620
```

- [ ] **Step 2: Run test, verify fail** — `pytest tests/test_config.py -v` → FAIL (no module attrs)

- [ ] **Step 3: Implement `src/config.py`**
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"

SEED = 20260620

# Underwriting policy (doc 03 §6/§7)
PD_APPROVE = 0.06
PD_DECLINE = 0.12
RISK_GRADE_BANDS = [("A", 0.02), ("B", 0.05), ("C", 0.10), ("D", 0.20), ("E", 1.01)]  # upper bounds

# Fraud policy (doc 04 §7)
FRAUD_THRESHOLDS = {"approve": 0.35, "stepup": 0.60, "review": 0.80, "block": 1.01}
# Stablecoin policy (doc 04 §8)
STABLECOIN_THRESHOLDS = {"monitor": 0.40, "review": 0.65, "high_risk": 0.85}

# Expected-loss assumptions (doc 05) — all labeled assumptions
LGD_BY_RISK = {"low": 0.35, "standard": 0.55, "high": 0.75}
LGD_DEFAULT = 0.55
UTILIZATION_ASSUMPTION = 0.65
FRAUD_LOSS_SEVERITY = 0.90
STRESS = {
    "base":     {"pd_mult": 1.00, "lgd_mult": 1.00, "fraud_mult": 1.00},
    "moderate": {"pd_mult": 1.25, "lgd_mult": 1.10, "fraud_mult": 1.20},
    "severe":   {"pd_mult": 1.60, "lgd_mult": 1.25, "fraud_mult": 1.50},
}
PSI_BANDS = {"stable": 0.10, "monitor": 0.25}

# Manual-review capacity assumption (doc 04 §10 / 07 §4) — labeled
MANUAL_REVIEW_CAPACITY = 250

# Data sampling
CREDIT_SAMPLE_ROWS = 70000
FRED_SERIES = {
    "unemployment_rate": "UNRATE",
    "policy_rate": "FEDFUNDS",
    "inflation_cpi": "CPIAUCSL",          # -> YoY inflation_rate
    "consumer_credit_delinquency_rate": "DRCCLACBS",
    "credit_card_chargeoff_rate": "CORCCACBS",
}
KAGGLE_CREDIT = "wordsforthewise/lending-club"
KAGGLE_FRAUD = "mlg-ulb/creditcardfraud"

ROUND_DP = 6
```

- [ ] **Step 4: Run test, verify pass** — `pytest tests/test_config.py -v` → PASS

- [ ] **Step 5: Commit**
```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): central thresholds, assumptions, paths, seed"
```

### Task 1.3: `src/reporting/writers.py` — deterministic writers

**Files:** Create `src/reporting/writers.py`; Test `tests/test_writers.py`

- [ ] **Step 1: Failing test**
```python
# tests/test_writers.py
import json, pandas as pd
from src.reporting import writers

def test_write_json_sorted_and_rounded(tmp_path):
    p = tmp_path / "x.json"
    writers.write_json(p, {"b": 1.123456789, "a": 2})
    txt = p.read_text()
    assert txt.index('"a"') < txt.index('"b"')          # sorted keys
    assert json.loads(txt)["b"] == 1.123457              # rounded 6dp

def test_write_csv_rounds_floats(tmp_path):
    p = tmp_path / "x.csv"
    writers.write_csv(p, pd.DataFrame({"v": [1.123456789]}))
    assert "1.123457" in p.read_text()
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement** — `write_json(path, obj)` recursively rounds floats to `config.ROUND_DP`, dumps with `sort_keys=True, indent=2`, converts numpy types to builtins; `write_csv(path, df)` rounds float columns to `ROUND_DP`, writes `index=False`. Both `mkdir(parents=True, exist_ok=True)`.

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit** — `git commit -m "feat(reporting): deterministic json/csv writers"`

---

## Phase 2 — Data layer

> Order: macro (simplest real pull) → credit → payments → stablecoin → features/model-datasets → splits → quality+leakage gate. Each ingest caches raw in `data/raw/` and writes a `data/processed/*.csv`.

### Task 2.1: FRED macro ingest

**Files:** Create `src/data/ingest_macro.py`; Test `tests/test_macro.py`
Output: `data/processed/macro_stress_inputs.csv` (doc 02 §7) — columns: `date, unemployment_rate, policy_rate, inflation_rate, consumer_credit_delinquency_rate, credit_card_chargeoff_rate`.

- [ ] **Step 1: Failing test**
```python
# tests/test_macro.py
import pandas as pd
from src import config
from src.data import ingest_macro

def test_macro_schema_and_inflation():
    df = ingest_macro.run()
    need = {"date","unemployment_rate","policy_rate","inflation_rate",
            "consumer_credit_delinquency_rate","credit_card_chargeoff_rate"}
    assert need.issubset(df.columns)
    assert (config.PROCESSED / "macro_stress_inputs.csv").exists()
    assert df["inflation_rate"].notna().sum() > 0          # YoY computed
    assert len(df) > 24
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement** — for each series in `config.FRED_SERIES`, GET `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>` (timeout 30, cache CSV to `data/raw/fred_<id>.csv`; reuse cache if present). Parse to monthly, merge on month. `inflation_rate` = YoY % change of `CPIAUCSL` (×100). Restrict to a common date window (e.g. 2007-01 onward to align with LendingClub). Record pull date to `data/raw/fred_pull_date.txt`. Write via `writers.write_csv`. `run()` returns the DataFrame.

- [ ] **Step 4: Run, verify pass** — `pytest tests/test_macro.py -v` (network)

- [ ] **Step 5: Commit** — `git commit -m "feat(data): FRED macro ingest with YoY inflation"`

### Task 2.2: LendingClub credit ingest (download + stratified sample + clean + leakage filter)

**Files:** Create `src/data/ingest_credit.py`; Test `tests/test_credit.py`
Output: `data/processed/processed_credit_applicants.csv` — schema per spec §5.1 (doc 02 §4 minimum fields + `default_flag` + `loss_amount_if_default` + `is_synthetic_reject` flag).

- [ ] **Step 1: Failing tests**
```python
# tests/test_credit.py
import pandas as pd
from src import config
from src.data import ingest_credit

LEAK = {"recoveries","collection_recovery_fee","total_pymnt","total_rec_prncp",
        "last_pymnt_d","last_pymnt_amnt","out_prncp","next_pymnt_d","loan_status"}

def test_schema_target_and_no_leakage():
    df = ingest_credit.run()
    need = {"applicant_id","application_date","loan_amount","annual_income",
            "debt_to_income","employment_length","credit_grade","interest_rate",
            "loan_purpose","home_ownership","delinquency_history",
            "revolving_utilization","open_accounts","default_flag","loss_amount_if_default"}
    assert need.issubset(df.columns)
    assert set(df["default_flag"].dropna().unique()) <= {0,1}
    assert not (LEAK & set(df.columns))                       # leakage columns dropped
    # default proxy: only allowed statuses survived (Current/Grace/Late16-30 dropped) -> both classes present
    assert df["default_flag"].nunique() == 2

def test_sample_preserves_years_for_splits():
    df = ingest_credit.run()
    yrs = pd.to_datetime(df["application_date"]).dt.year.value_counts()
    assert (yrs >= 100).sum() >= 5          # multiple usable vintages
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement** —
  - Download `accepted_2007_to_2018Q4.csv.gz` via kaggle API to `data/raw/` if not cached (`KaggleApi().dataset_download_file(config.KAGGLE_CREDIT, "accepted_2007_to_2018Q4.csv.gz", path=RAW)`).
  - Read in chunks (`pd.read_csv(gz, chunksize=200_000, low_memory=False, usecols=<application-time + loan_status + issue_d>)`). Keep only rows whose `loan_status` is in the keep-set; assign `default_flag` proxy (spec §5.1): 1 for `Charged Off|Default|Late (31-120 days)|Does not meet the credit policy. Status:Charged Off`, 0 for `Fully Paid`; drop others.
  - **Stratified seeded sample** to `config.CREDIT_SAMPLE_ROWS`: group by (issue year, default_flag), sample proportionally with `random_state=config.SEED`, so each vintage retains rows for time-aware splits.
  - Map raw→schema columns (spec §5.1). Clean: `int_rate`/`revol_util` strip `%`→float; `emp_length`→numeric years; `term`/dates parsed; `dti` numeric.
  - `loss_amount_if_default = loan_amount * LGD(risk)` (assumption; LGD chosen later by grade — store base estimate using `LGD_DEFAULT`, recomputed precisely in expected-loss).
  - **Drop every leakage column** (LEAK set + any post-origination field) and drop raw `loan_status` after deriving target.
  - Append rejects: sample `rejected_*` file + generate clearly-labeled synthetic rejects; set `is_synthetic_reject` flag; rejects carry NaN `default_flag` (never used for PD training).
  - Write via `writers.write_csv`. `run()` returns accepted+rejects (accepted have default_flag).

- [ ] **Step 4: Run, verify pass** (downloads ~400MB first run; cached after)

- [ ] **Step 5: Commit** — `git commit -m "feat(data): LendingClub ingest, default proxy, leakage filter, stratified sample"`

### Task 2.3: Kaggle fraud ingest + synthetic labeled context

**Files:** Create `src/data/ingest_payments.py`; Test `tests/test_payments.py`
Output: `data/processed/processed_payment_transactions.csv` — doc 04 §3 schema + real `V1..V28` + `is_synthetic_context` marker column.

- [ ] **Step 1: Failing tests**
```python
# tests/test_payments.py
import pandas as pd
from src import config
from src.data import ingest_payments

def test_real_labels_and_synthetic_context():
    df = ingest_payments.run()
    need = {"transaction_id","account_id","transaction_time","amount",
            "merchant_category","merchant_risk_band","location_proxy","device_proxy",
            "account_age_days","transaction_count_24h","amount_count_24h",
            "fraud_flag","chargeback_loss"}
    assert need.issubset(df.columns)
    assert set(df["fraud_flag"].unique()) <= {0,1}
    assert df["fraud_flag"].mean() < 0.02          # real imbalance preserved (~0.17%)
    assert any(c.startswith("V") for c in df.columns)   # real PCA features kept
    assert df["is_synthetic_context"].all()             # context flagged synthetic
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement** — download `creditcard.csv` via kaggle if not cached; `fraud_flag=Class`; keep `Time, Amount, V1..V28`. Seeded synthetic context: assign `account_id` (e.g. 1–2000), sort by `Time`, derive `transaction_count_24h`/`amount_count_24h`/`velocity` from real `Time` ordering within account; synthesize `merchant_category, merchant_risk_band, location_proxy, device_proxy, account_age_days, chargeback_loss` (`= Amount` when fraud else 0). `transaction_time` = base date + `Time` seconds. Mark `is_synthetic_context=True`. Write via writer.

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit** — `git commit -m "feat(data): Kaggle fraud ingest + labeled synthetic context"`

### Task 2.4: Synthetic stablecoin ingest

**Files:** Create `src/data/ingest_stablecoin.py`; Test `tests/test_stablecoin_data.py`
Output: `data/processed/processed_stablecoin_transactions.csv` — doc 02 §6 schema.

- [ ] **Step 1: Failing test** — assert schema columns present, `amount_usd>0`, `counterparty_risk_score∈[0,1]`, `stablecoin_risk_label∈{0,1}`, `is_synthetic.all()`, rows ≥ 2000.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — seeded generator (`np.random.default_rng(config.SEED)`) producing fields in doc 02 §6 with plausible distributions (wallet ages, inflow/outflow, counterparty risk, risky-address exposure). Mark `is_synthetic=True`. Write.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(data): synthetic stablecoin transactions"`

### Task 2.5: Feature engineering + model datasets

**Files:** Create `src/data/features.py`; Test `tests/test_features.py`
Outputs: `data/processed/underwriting_model_dataset.csv`, `fraud_model_dataset.csv`, `validation_dataset.csv`.

- [ ] **Step 1: Failing tests**
```python
# tests/test_features.py
from src.data import features
LEAK = {"recoveries","collection_recovery_fee","total_pymnt","last_pymnt_amnt","out_prncp","loan_status"}
def test_underwriting_features_present_no_leakage():
    uw, fr, val = features.run()
    for c in ["income_to_loan_ratio","debt_burden_score","credit_utilization_band",
              "loan_size_band","credit_grade_numeric","prior_delinquency_flag","application_vintage"]:
        assert c in uw.columns
    assert not (LEAK & set(uw.columns))
    assert uw["default_flag"].notna().all()       # rejects excluded from PD dataset
def test_fraud_features_present():
    uw, fr, val = features.run()
    for c in ["velocity_1h","velocity_24h","amount_zscore_by_account","merchant_risk_score",
              "new_device_flag","new_location_flag","night_transaction_flag","high_amount_flag"]:
        assert c in fr.columns
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — read processed credit/payments; build engineered features (spec §5.1/§5.2). `underwriting_model_dataset` = accepted-only (drop synthetic rejects; `default_flag` non-null). `fraud_model_dataset` = payments + engineered. `validation_dataset` = held-out concatenation used by validation (carry split label from Task 2.6 or recompute). Write all three.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(data): engineered features + model datasets"`

### Task 2.6: Time-aware splits + data-quality + leakage gate

**Files:** Create `src/data/splits.py`, `src/data/quality.py`; Test `tests/test_quality.py`
Output: `data/outputs/data_quality_report.csv` (doc 08 §11). Adds `split` column (train/val/test) to model datasets.

- [ ] **Step 1: Failing tests**
```python
# tests/test_quality.py
import pandas as pd
from src import config
from src.data import splits, quality

def test_time_split_no_overlap_and_ordered():
    s = splits.time_split(pd.DataFrame({"d": pd.date_range("2010-01-01", periods=100, freq="D")}), "d")
    assert s["train"].max() < s["val"].min() <= s["val"].max() < s["test"].min()

def test_quality_report_and_leakage_pass():
    rep = quality.run()
    need = {"dataset_name","row_count","column_count","missing_value_count",
            "duplicate_id_count","target_rate","date_min","date_max",
            "leakage_check_status","schema_check_status"}
    assert need.issubset(rep.columns)
    assert (rep["leakage_check_status"] == "pass").all()    # STOP build otherwise
    assert (config.OUTPUTS / "data_quality_report.csv").exists()
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `splits.time_split(df, date_col)` → dict of index arrays for earliest 70 / next 15 / latest 15%; applied per dataset by date (credit `application_date`, payments `transaction_time`). `quality.run()` computes the report row per processed dataset; **leakage check**: assert no forbidden column (doc 02 §4 + doc 04 §15 lists) present in any model dataset, and that `default_flag`/`fraud_flag` not derived from post-event fields; set status `pass`/`fail`. If any `fail`, `quality.run()` raises `LeakageError` (build stops). Write report.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(data): time-aware splits + data quality + leakage gate"`

---

## Phase 3 — Underwriting engine (doc 03)

### Task 3.1: Champion + challenger models with PD calibration

**Files:** Create `src/models/scorecard.py`, `src/models/gbm.py`, `src/models/calibration.py`, `src/models/metrics.py`; Test `tests/test_models.py`

- [ ] **Step 1: Failing tests**
```python
# tests/test_models.py
import numpy as np
from src.models import metrics, calibration
def test_metrics_ranges():
    y = np.array([0,0,1,1,0,1]); s = np.array([.1,.2,.8,.7,.3,.9])
    assert 0 <= metrics.roc_auc(y,s) <= 1
    assert 0 <= metrics.pr_auc(y,s) <= 1
    assert 0 <= metrics.brier(y,s) <= 1
    assert 0 <= metrics.ks(y,s) <= 1
def test_calibration_outputs_probabilities():
    y = np.random.RandomState(0).randint(0,2,500); s = np.random.RandomState(1).rand(500)
    cal = calibration.fit(s, y); p = cal.transform(s)
    assert ((p>=0)&(p<=1)).all()
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `metrics`: thin wrappers over `sklearn.metrics` (roc_auc_score, average_precision_score, brier_score_loss) + KS (max |CDF diff|) + `confusion_at(y,s,thr)` + `psi(expected,actual,bins=10)`. `scorecard.fit(X,y)`: `Pipeline(StandardScaler, LogisticRegression(max_iter=1000, random_state=SEED))`, expose coefficients. `gbm.fit(X,y)`: `GradientBoostingClassifier(random_state=SEED)` + feature_importances_. `calibration.fit(scores,y)`: isotonic (`IsotonicRegression(out_of_bounds="clip")`) fit on validation; `transform` clips to [0,1]; report pre/post Brier + curve points.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(models): logreg champion, gbm challenger, calibration, metrics"`

### Task 3.2: Underwriting policy — grade, decision, limit, reason codes

**Files:** Create `src/risk/underwriting.py`; Test `tests/test_underwriting.py`

- [ ] **Step 1: Failing tests**
```python
# tests/test_underwriting.py
from src.risk import underwriting as uw
from src import config
def test_grade_and_decision_bands():
    assert uw.risk_grade(0.01)=="A" and uw.risk_grade(0.03)=="B" and uw.risk_grade(0.25)=="E"
    assert uw.decision(0.05)=="approve" and uw.decision(0.09)=="review" and uw.decision(0.20)=="decline"
def test_reason_codes_explainable_nonempty():
    row = {"debt_to_income":45,"income_to_loan_ratio":0.5,"revolving_utilization":95,
           "prior_delinquency_flag":1,"credit_grade":"E","loan_amount":40000,"PD":0.3}
    rc = uw.reason_codes(row)
    assert 1 <= len(rc) <= 3
    assert all(r in uw.ALLOWED_REASONS for r in rc)   # no "model says risky"
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `risk_grade(pd)` via `config.RISK_GRADE_BANDS`; `decision(pd)` via `PD_APPROVE/PD_DECLINE`; `recommended_limit(row)` from PD + income coverage + DTI (doc 03 §8 rule); `ALLOWED_REASONS` mapping (doc 03 §10) + `reason_codes(row)` returns top 1–3 triggered drivers (high DTI, low income-to-loan, high utilization, prior delinquency, weak grade, large loan, high PD). All explainable strings.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): underwriting grade/decision/limit/reason-codes"`

### Task 3.3: Underwriting outputs

**Files:** Modify `src/risk/underwriting.py` (add `build()`); Test `tests/test_underwriting_outputs.py`
Outputs: `underwriting_decisions.csv`, `underwriting_decisions.json`, `underwriting_policy_summary.json`.

- [ ] **Step 1: Failing test** — `underwriting.build()` then assert each applicant row has doc 03 §11 columns (`applicant_id,PD,risk_grade,decision,recommended_credit_limit,LGD,EAD,expected_loss,top_reason_1..3,model_used`); `PD∈[0,1]`; policy summary JSON has `approval_rate,review_rate,decline_rate,default_rate_by_decision,expected_loss_by_decision` and chart blocks (PD distribution, grade distribution, approval mix, EL by grade, top decline reasons) embedded.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — train champion+challenger on `underwriting_model_dataset` train split; calibrate on val; PD on all accepted; choose `model_used` per applicant = champion (default; challenger reported in validation). Compute grade/decision/limit/reason codes; attach LGD/EAD/EL placeholders (final EL recomputed in Phase 6, but underwriting EL fields populated using config assumptions here for self-consistency). Write CSV/JSON + policy summary with embedded chart arrays.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): underwriting outputs + policy summary"`

---

## Phase 4 — Fraud & payments engine (doc 04)

### Task 4.1: Rules + supervised + anomaly → fraud_score

**Files:** Create `src/risk/fraud.py`, `src/models/anomaly.py`; Test `tests/test_fraud_score.py`
- [ ] **Step 1: Failing tests** — `anomaly.fit/score` returns normalized [0,1]; `fraud.score_frame(df)` returns `fraud_probability∈[0,1]`, `fraud_score∈[0,1]`, `anomaly_score∈[0,1]`; supervised PR-AUC computed and reported (headline), accuracy not used as headline.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — rules engine (doc 04 §6A booleans → rule_score); supervised model on `fraud_model_dataset` train split using `V1..V28`+engineered (LogisticRegression or GradientBoosting; class_weight/scale for imbalance), output `fraud_probability`; anomaly (`IsolationForest(random_state=SEED)` / LOF) normalized to [0,1]; blend into `fraud_score` (documented weighting). Report PR-AUC, precision, recall, capture rate, FPR/FNR.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): fraud rules+supervised+anomaly scoring"`

### Task 4.2: Action mapping, expected fraud loss, review queue

**Files:** Modify `src/risk/fraud.py`; Test `tests/test_fraud_actions.py`
- [ ] **Step 1: Failing tests** — `fraud.action(score)` ∈ {approve,step_up,review,block} per `config.FRAUD_THRESHOLDS`; `expected_fraud_loss = fraud_probability*amount*FRAUD_LOSS_SEVERITY ≥ 0`; manual-review queue size ≤ `MANUAL_REVIEW_CAPACITY` (capacity-aware ranking by expected loss).
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — action map; expected fraud loss; `manual_review_priority` ranked by expected loss within capacity; cost-by-threshold tradeoff arrays.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): fraud actions, expected loss, capacity-aware queue"`

### Task 4.3: Fraud outputs

**Files:** Modify `src/risk/fraud.py` (`build()`); Test `tests/test_fraud_outputs.py`
Outputs: `fraud_alerts.csv`, `fraud_alerts.json`, `fraud_policy_summary.json`.
- [ ] **Step 1: Failing test** — each tx row has doc 04 §13 columns (`transaction_id,account_id,transaction_time,amount,fraud_score,anomaly_score,payment_action,expected_fraud_loss,top_reason_1..3,manual_review_priority`); policy summary has action mix, score distribution, EL by action, queue size, top drivers, threshold-tradeoff arrays (PR-AUC headline).
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** `fraud.build()` writing the three files with embedded chart arrays.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): fraud outputs + policy summary"`

---

## Phase 5 — Stablecoin module (doc 04 §4/§8)

### Task 5.1: Wallet-risk scoring + action + exposure

**Files:** Create `src/risk/stablecoin.py`; Test `tests/test_stablecoin.py`
- [ ] **Step 1: Failing tests** — `stablecoin.score_frame(df)` → `stablecoin_risk_score∈[0,1]`, `risk_exposure_score≥0`; `stablecoin.action(score)` ∈ {normal,monitor,review,high_risk} per `config.STABLECOIN_THRESHOLDS`; reason codes from allowed AML-style set; no "AML compliance" string anywhere in module output.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — composite wallet-risk score from velocity, counterparty risk, inflow/outflow ratio, risky-address exposure, large-transfer/new-counterparty flags (doc 04 §4 engineered features); action map; `risk_exposure = score*amount_usd`; AML-style reason codes.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): stablecoin wallet-risk scoring + actions"`

### Task 5.2: Stablecoin outputs

**Files:** Modify `src/risk/stablecoin.py` (`build()`); Test `tests/test_stablecoin_outputs.py`
Outputs: `stablecoin_alerts.csv`, `stablecoin_alerts.json`.
- [ ] **Step 1: Failing test** — each row has doc 04 §13 columns (`wallet_id,counterparty_wallet_id,transaction_time,amount_usd,stablecoin_risk_score,stablecoin_risk_action,risk_exposure_score,top_reason_1..3`); JSON has action mix, high-risk wallet count, exposure by action, wallet-risk leaderboard.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** `build()`.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): stablecoin outputs"`

---

## Phase 6 — Expected-loss engine (doc 05)

### Task 6.1: Credit EL + fraud EL + stablecoin exposure

**Files:** Create `src/risk/expected_loss.py`; Test `tests/test_el_core.py`
- [ ] **Step 1: Failing tests**
```python
from src.risk import expected_loss as el
from src import config
def test_el_formula_and_ranges():
    r = el.credit_el(pd_=0.1, risk_grade="C", loan_amount=10000, limit=8000, revolving=False)
    assert r["LGD"] == config.LGD_BY_RISK["standard"] or 0 <= r["LGD"] <= 1
    assert r["EAD"] >= 0 and r["expected_loss"] >= 0
    assert abs(r["expected_loss"] - r["PD"]*r["LGD"]*r["EAD"]) < 1e-9
def test_lgd_ead_bounds():
    assert 0 <= el.lgd_for("A") <= 1 and 0 <= el.lgd_for("E") <= 1
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `lgd_for(grade)` maps A/B→low, C/D→standard, E→high (documented); `credit_el(...)` EAD = loan_amount (installment) or limit×`UTILIZATION_ASSUMPTION` (revolving); EL=PD×LGD×EAD; `expected_loss_rate=EL/EAD`; `net_expected_value=interest_rate*EAD-EL`. `fraud_el(p,amount)=p*amount*FRAUD_LOSS_SEVERITY`. `stablecoin_exposure(score,amount)=score*amount`.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): expected-loss core formulas"`

### Task 6.2: Segment views + reconciliation

**Files:** Modify `src/risk/expected_loss.py`; Test `tests/test_el_segments.py`
- [ ] **Step 1: Failing test** — segment aggregations (doc 05 §9 dimensions) each include `total_expected_loss,average_expected_loss,expected_loss_rate,account_count,exposure`; **sum of segment `total_expected_loss` == portfolio total within 1e-6** (else raise `ReconciliationError`).
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `aggregate_loss(df, by)` helper; build per-dimension tables; assert reconciliation.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): EL segment views + reconciliation"`

### Task 6.3: Stress + policy loss comparison + outputs

**Files:** Modify `src/risk/expected_loss.py` (`build()`); Test `tests/test_el_outputs.py`
Outputs: `expected_loss_applicant_level.csv`, `expected_loss_summary.json`, `expected_loss_by_segment.json`, `stress_loss_summary.json`, `policy_loss_comparison.json`.
- [ ] **Step 1: Failing tests** — applicant rows have `applicant_id,PD,LGD,EAD,expected_loss,expected_loss_rate,base_loss,moderate_stress_loss,severe_stress_loss`; `severe_stress_loss ≥ moderate_stress_loss ≥ base_loss`; **stressed PD capped at 1**; policy_loss_comparison has approval/review/decline rates + losses per threshold.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — apply `config.STRESS` multipliers (PD capped 1.0); segment + summary + stress + policy-loss outputs with embedded chart arrays (EL by grade/decision, waterfall, base-vs-stressed, approval-vs-loss, policy threshold curve).
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): stress cases, policy loss comparison, EL outputs"`

---

## Phase 7 — Model-risk validation (doc 06)

### Task 7.1: Metrics + calibration + drift + segments

**Files:** Create `src/validation/validate.py`; Test `tests/test_validation_core.py`
- [ ] **Step 1: Failing tests** — credit validation produces ROC-AUC, PR-AUC, Brier, KS, confusion@policy, calibration curve points, decile default table, PSI (train vs test) with band label; fraud validation produces PR-AUC headline + precision/recall/capture/FPR/FNR; segment performance table per doc 06 §9 dims.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — compute all metrics on held-out splits; calibration curve + decile default table (embedded later); PSI via `metrics.psi`; segment metrics; flag weak segments.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(validation): metrics, calibration, drift, segments"`

### Task 7.2: Champion/challenger + verdicts

**Files:** Modify `src/validation/validate.py`; Test `tests/test_verdicts.py`
- [ ] **Step 1: Failing tests** — `champion_challenger` compares ROC/PR-AUC, Brier, calibration, stability, segment weakness (not auto-highest-AUC); each model verdict ∈ {Pass,Monitor,Fail} with one-sentence `verdict_reason`; verdict consistent with metrics (e.g., Fail not assigned to a model with strong calibration+performance, and vice-versa).
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — verdict rules (doc 06 §13): Pass = acceptable performance+calibration+stability+explainability; Monitor = usable w/ weakness/drift; Fail = unreliable. Final choice weighs calibration+explainability.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(validation): champion/challenger + verdicts"`

### Task 7.3: Validation outputs (with embedded calibration curve + decile table)

**Files:** Modify `src/validation/validate.py` (`build()`); Test `tests/test_validation_outputs.py`
Outputs: `model_validation_summary.json`, `credit_model_validation.csv`, `fraud_model_validation.csv`, `stablecoin_model_validation.csv`, `champion_challenger_comparison.json`, `model_risk_verdicts.json`.
- [ ] **Step 1: Failing test** — verdict rows have doc 06 §14 columns; `model_validation_summary.json` **embeds** `calibration_curve` + `decile_default_table` + `predicted_vs_actual_by_band` (per spec §7 chart-data rule — no separate files); decile table also present in `credit_model_validation.csv`.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** `build()` writing six files; embed calibration/decile/segment-heatmap/PR-curve chart arrays inside the JSON.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(validation): outputs with embedded calibration+decile chart data"`

---

## Phase 8 — Policy simulator data (doc 07)

### Task 8.1: Threshold grid + scenarios + constraints + warnings

**Files:** Create `src/risk/policy_simulator.py`; Test `tests/test_simulator.py`
- [ ] **Step 1: Failing tests**
```python
from src.risk import policy_simulator as ps
def test_constraints_reject_invalid():
    assert not ps.valid_config(pd_approve=0.2, pd_decline=0.1)        # approve<decline
    assert ps.valid_config(pd_approve=0.06, pd_decline=0.12)
def test_warnings_are_specific():
    w = ps.warnings_for(review_volume=295, capacity=250, uncalibrated=False, verdict="Pass")
    assert any("%" in s for s in w)                                   # quantified
    assert "Risk is high." not in w
```

- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `valid_config(...)` enforces ordering + ranges (doc 07 §10); `simulate(scenario)` recomputes decision mix, losses, review volume, blocked rate from precomputed applicant/tx scores; `warnings_for(...)` emits specific strings ("manual review volume exceeds capacity by 18%", "policy uses uncalibrated PD", "segment loss concentrated in grade E", verdict Monitor/Fail). Build a grid over PD/fraud/stablecoin thresholds × stress presets.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): policy simulator grid, constraints, specific warnings"`

### Task 8.2: Simulator outputs

**Files:** Modify `src/risk/policy_simulator.py` (`build()`); Test `tests/test_simulator_outputs.py`
Outputs: `policy_simulator_inputs.json`, `policy_simulator_results.json`, `policy_threshold_grid.csv`.
- [ ] **Step 1: Failing test** — inputs JSON has control definitions + defaults (doc 07 §3–6); each scenario row has doc 07 §11 columns (`scenario_id,credit_pd_cutoff,fraud_threshold,stablecoin_threshold,approval_rate,review_rate,decline_rate,expected_credit_loss,expected_fraud_loss,stablecoin_risk_exposure,total_expected_loss,manual_review_volume,model_risk_flag`); grid CSV non-empty.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** `build()`.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(risk): policy simulator outputs"`

---

## Phase 9 — Reporting, reconciliation, orchestrator

### Task 9.1: Risk command center + methodology

**Files:** Create `src/reporting/command_center.py`, `src/reporting/methodology.py`; Test `tests/test_reporting.py`
Outputs: `risk_command_center.json`, `methodology_summary.json`.
- [ ] **Step 1: Failing test** — command center has doc 08 §5 keys (`total_applicants,approval_rate,review_rate,decline_rate,average_PD,total_approved_exposure,total_expected_credit_loss,total_expected_fraud_loss,stablecoin_risk_exposure,manual_review_volume,model_verdict_summary,highest_risk_segment`); methodology has doc 08 §12 keys + `synthetic_data_disclosure` + `chart_data_embedding_map` + `default_flag_definition` (labeled proxy) + dataset versions + FRED pull date; **no forbidden claim strings** present (scan against forbidden list).
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — assemble from existing outputs; methodology lists real-vs-synthetic per domain, default proxy definition, LGD/EAD/severity/stress assumptions, validation methods, known limitations, and the chart-embedding map.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(reporting): command center + methodology"`

### Task 9.2: Reconciliation gate + required-output check

**Files:** Create `src/reporting/reconcile.py`; Test `tests/test_reconcile.py`
- [ ] **Step 1: Failing tests** — `reconcile.required_outputs()` asserts all 9 CSV + 16 JSON in `data/outputs` + 7 processed exist & non-empty (raise `MissingOutputError` otherwise); `reconcile.totals()` checks applicant/transaction/segment/loss totals match across files and verdicts match metrics (raise `ReconciliationError` otherwise).
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — the two gate functions with the canonical file list from spec §7.
- [ ] **Step 4: Run, verify pass**
- [ ] **Step 5: Commit** — `git commit -m "feat(reporting): reconciliation + required-output gates"`

### Task 9.3: Orchestrator + full run + determinism

**Files:** Create `src/run_pipeline.py`; Test `tests/test_pipeline_determinism.py`
- [ ] **Step 1: Failing test** — run pipeline twice; assert byte-identical `risk_command_center.json` and `underwriting_decisions.csv` (determinism); assert `reconcile.required_outputs()` and `reconcile.totals()` pass.
- [ ] **Step 2: Run, verify fail**
- [ ] **Step 3: Implement** — `main()` runs phases in order: macro→credit→payments→stablecoin→features→splits/quality(leakage gate)→underwriting→fraud→stablecoin→expected_loss→validation→policy_simulator→reporting→reconcile gates. Fail-fast on any gate exception with a clear message.
- [ ] **Step 4: Run full pipeline** — `python -m src.run_pipeline` → populated `data/outputs`; then `pytest -q` all green.
- [ ] **Step 5: Commit** — `git commit -m "feat: end-to-end pipeline, determinism + reconciliation green"` and commit `data/outputs` + `data/processed` (deliverables).

---

## Self-Review

**Spec coverage:** P1 §4 ✓; data layer §5 (macro/credit/payments/stablecoin/features/splits/quality) ✓ Tasks 2.1–2.6; underwriting §6.1 ✓ P3; fraud §6.2 ✓ P4; stablecoin §6.3 ✓ P5; expected-loss §6.4 ✓ P6; validation §6.5 ✓ P7; simulator §6.6 ✓ P8; reporting+reconcile §6.7/§7 ✓ P9; output contract §7 (25 files) ✓ Task 9.2; honesty/labeling ✓ Tasks 2.2/2.3/9.1; stop conditions ✓ (LeakageError 2.6, ReconciliationError 6.2/9.2, MissingOutputError 9.2); determinism ✓ 9.3. Design-system/frontend (§8/§9) → Plan 2 (intentional split).
**Placeholder scan:** code shown for contract-critical parts (config, metrics, formulas, schemas, test assertions); mechanical column mapping references spec §5/docs by exact field lists — no vague "add validation"/"TBD".
**Type consistency:** `config.*` names used identically across tasks; `risk_grade/decision/reason_codes/action/credit_el/fraud_el/score_frame/build/run` signatures consistent across phases; gate exceptions (`LeakageError`, `ReconciliationError`, `MissingOutputError`) defined where raised and reused in 9.2/9.3.
