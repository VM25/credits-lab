from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"

SEED = 20260620

# Underwriting policy (doc 03)
# Validation-derived default operating point for the 21%-base-rate accepted book
# (model rank-orders/calibrates well; see decile evidence). Doc reference cutoffs
# 0.06/0.12 retained below for the policy simulator.
PD_APPROVE = 0.15
PD_DECLINE = 0.30
# Doc reference thresholds — retained for the Phase 8 policy simulator
DOC_REFERENCE_PD_THRESHOLDS = {"approve": 0.06, "decline": 0.12}
# Validation-rescaled from doc's starting bands to spread across this book's PD distribution
RISK_GRADE_BANDS = [("A", 0.10), ("B", 0.18), ("C", 0.28), ("D", 0.40), ("E", 1.01)]  # upper bounds

# Fraud policy (doc 04)
FRAUD_THRESHOLDS = {"approve": 0.35, "stepup": 0.60, "review": 0.80, "block": 1.01}
# Stablecoin policy (doc 04)
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

# Manual-review capacity assumption (labeled)
MANUAL_REVIEW_CAPACITY = 250

# Data sampling / sources
CREDIT_SAMPLE_ROWS = 70000
PAYMENTS_SAMPLE_ROWS = 80000
STABLECOIN_ROWS = 2500
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

# Display-sample size for large row-level JSONs
UI_SAMPLE_ROWS = 1500
