import json

import pandas as pd

from src import config
from src.risk import expected_loss as el


def test_el_formula_and_bounds():
    r = el.credit_el(pd_=0.1, risk_grade="C", loan_amount=10000, limit=8000, revolving=False)
    assert r["EAD"] == 10000  # installment EAD = loan_amount
    assert 0 <= r["LGD"] <= 1 and r["EAD"] >= 0 and r["expected_loss"] >= 0
    assert abs(r["expected_loss"] - r["PD"] * r["LGD"] * r["EAD"]) < 1e-9
    # revolving uses limit * utilization
    rv = el.credit_el(pd_=0.1, risk_grade="C", loan_amount=10000, limit=8000, revolving=True)
    assert abs(rv["EAD"] - 8000 * config.UTILIZATION_ASSUMPTION) < 1e-9
    assert 0 <= el.lgd_for("A") <= 1 and 0 <= el.lgd_for("E") <= 1
    assert el.fraud_el(0.5, 100) == 0.5 * 100 * config.FRAUD_LOSS_SEVERITY
    assert el.fraud_el(0.0, 100) == 0.0


def test_build_outputs_and_reconciliation():
    el.build()
    df = pd.read_csv(config.OUTPUTS / "expected_loss_applicant_level.csv")
    need = {"applicant_id", "PD", "LGD", "EAD", "expected_loss", "expected_loss_rate",
            "base_loss", "moderate_stress_loss", "severe_stress_loss"}
    assert need.issubset(df.columns)
    # stress monotonic and PD-capped
    assert (df["severe_stress_loss"] >= df["moderate_stress_loss"] - 1e-9).all()
    assert (df["moderate_stress_loss"] >= df["base_loss"] - 1e-9).all()

    seg = json.load(open(config.OUTPUTS / "expected_loss_by_segment.json"))
    portfolio = seg["portfolio_expected_credit_loss"]
    # every credit segment dimension reconciles to the portfolio total
    for dim, rows in seg["credit_segments"].items():
        total = round(sum(r["total_expected_loss"] for r in rows), 2)
        assert abs(total - portfolio) <= 0.5, (dim, total, portfolio)

    summ = json.load(open(config.OUTPUTS / "expected_loss_summary.json"))
    for k in ["total_expected_credit_loss", "total_expected_fraud_loss",
              "total_stablecoin_risk_exposure", "expected_loss_by_risk_grade",
              "expected_loss_by_decision"]:
        assert k in summ

    stress = json.load(open(config.OUTPUTS / "stress_loss_summary.json"))["scenarios"]
    assert stress["severe"]["expected_credit_loss"] >= stress["base"]["expected_credit_loss"]

    pol = json.load(open(config.OUTPUTS / "policy_loss_comparison.json"))["policies"]
    assert len(pol) >= 3
    # higher approve cutoff -> higher approval rate (monotonic growth lever)
    rates = [p["approval_rate"] for p in sorted(pol, key=lambda x: x["approve_cutoff"])]
    assert rates == sorted(rates)
