from src.risk import underwriting as uw


def test_grade_and_decision_bands():
    assert uw.risk_grade(0.01) == "A" and uw.risk_grade(0.03) == "B" and uw.risk_grade(0.25) == "E"
    assert uw.decision(0.05) == "approve" and uw.decision(0.09) == "review" and uw.decision(0.20) == "decline"


def test_lgd_ead():
    assert uw.lgd_for("A") == 0.35 and uw.lgd_for("C") == 0.55 and uw.lgd_for("E") == 0.75
    assert uw.ead_for(10000) == 10000


def test_reason_codes_explainable_nonempty():
    row = {"debt_to_income": 45, "income_to_loan_ratio": 0.5, "revolving_utilization": 95,
           "prior_delinquency_flag": 1, "credit_grade": "E", "credit_grade_numeric": 5,
           "loan_amount": 40000, "PD": 0.3}
    rc = uw.reason_codes(row)
    assert 1 <= len(rc) <= 3
    assert all(r in uw.ALLOWED_REASONS for r in rc)
