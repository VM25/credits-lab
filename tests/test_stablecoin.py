from src.risk import stablecoin as sc
from src import config


def test_action_bands():
    assert sc.action(0.30) == "normal" and sc.action(0.50) == "monitor"
    assert sc.action(0.70) == "review" and sc.action(0.90) == "high_risk"


def test_reason_codes_aml_style():
    row = {"counterparty_risk_score": 0.95, "risky_address_exposure_flag": 1,
           "wallet_velocity": 50, "large_transfer_flag": 1, "new_counterparty_flag": 1,
           "inflow_outflow_ratio": 9.0}
    rc = sc.reason_codes(row)
    assert 1 <= len(rc) <= 3 and all(r in sc.ALLOWED_REASONS for r in rc)
    # never claim AML compliance in any reason explanation
    assert all("compliance" not in sc.ALLOWED_REASONS[r].lower() for r in sc.ALLOWED_REASONS)
