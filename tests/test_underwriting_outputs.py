import json
import pandas as pd
from src import config
from src.risk import underwriting as uw


def test_outputs_schema_and_ranges():
    uw.build()
    df = pd.read_csv(config.OUTPUTS / "underwriting_decisions.csv")
    need = {"applicant_id", "PD", "risk_grade", "decision", "recommended_credit_limit",
            "LGD", "EAD", "expected_loss", "top_reason_1", "top_reason_2", "top_reason_3", "model_used"}
    assert need.issubset(df.columns)
    assert df["PD"].between(0, 1).all()
    assert set(df["decision"].unique()) <= {"approve", "review", "decline"}
    assert (df["expected_loss"] >= 0).all()
    summ = json.load(open(config.OUTPUTS / "underwriting_policy_summary.json"))
    for k in ["approval_rate", "review_rate", "decline_rate", "default_rate_by_decision",
              "expected_loss_by_decision"]:
        assert k in summ
    dj = json.load(open(config.OUTPUTS / "underwriting_decisions.json"))
    assert dj["is_sample"] is True and dj["sample_size"] == len(dj["rows"]) and \
        dj["row_count_total"] >= dj["sample_size"]
