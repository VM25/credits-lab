from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"

SEED = 20260620

# Underwriting policy (doc 03)
PD_APPROVE = 0.06
PD_DECLINE = 0.12
RISK_GRADE_BANDS = [("A", 0.02), ("B", 0.05), ("C", 0.10), ("D", 0.20), ("E", 1.01)]  # upper bounds

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
