import json

import pandas as pd

from src import config
from src.risk import policy_simulator as ps


def test_constraints_reject_invalid():
    assert not ps.valid_config(pd_approve=0.2, pd_decline=0.1)
    assert ps.valid_config(pd_approve=0.06, pd_decline=0.12)
    bad_fraud = {"approve": 0.6, "stepup": 0.35, "review": 0.8, "block": 1.01}
    assert not ps.valid_config(fraud_thresholds=bad_fraud)
    assert not ps.valid_config(multipliers=[1.0, 0.0])
    assert not ps.valid_config(capacity=-5)


def test_warnings_are_specific():
    w = ps.warnings_for(review_volume=295, capacity=250, uncalibrated=False, verdict="Pass")
    assert any("%" in s for s in w)
    assert "Risk is high." not in w
    # monitor verdict surfaces a specific model-risk warning
    w2 = ps.warnings_for(review_volume=10, capacity=250, uncalibrated=False, verdict="Monitor")
    assert any("Monitor" in s for s in w2)


def test_simulator_outputs():
    ps.build()
    inp = json.load(open(config.OUTPUTS / "policy_simulator_inputs.json"))
    assert "credit" in inp and "fraud" in inp and "stablecoin" in inp and "stress" in inp
    res = json.load(open(config.OUTPUTS / "policy_simulator_results.json"))
    scen = res["scenarios"]
    assert len(scen) > 0
    need = {"scenario_id", "credit_pd_cutoff", "fraud_threshold", "stablecoin_threshold",
            "approval_rate", "review_rate", "decline_rate", "expected_credit_loss",
            "expected_fraud_loss", "stablecoin_risk_exposure", "total_expected_loss",
            "manual_review_volume", "model_risk_flag"}
    assert need.issubset(scen[0].keys())
    # capacity respected in every scenario
    assert all(s["manual_review_volume"] <= config.MANUAL_REVIEW_CAPACITY for s in scen)
    # higher approve cutoff -> higher approval rate, holding other dims fixed
    base = [s for s in scen if s["stress_scenario"] == "base"
            and s["fraud_threshold"] == 0.60 and s["stablecoin_threshold"] == 0.85]
    base_sorted = sorted(base, key=lambda x: x["credit_pd_cutoff"])
    rates = [s["approval_rate"] for s in base_sorted]
    assert rates == sorted(rates)
    grid = pd.read_csv(config.OUTPUTS / "policy_threshold_grid.csv")
    assert len(grid) == len(scen)
