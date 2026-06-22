import json
import pandas as pd
from src import config
from src.risk import fraud


def test_fraud_outputs():
    fraud.build()
    df = pd.read_csv(config.OUTPUTS / "fraud_alerts.csv")
    need = {
        "transaction_id", "account_id", "transaction_time", "amount",
        "fraud_score", "anomaly_score", "payment_action", "expected_fraud_loss",
        "top_reason_1", "top_reason_2", "top_reason_3", "manual_review_priority",
    }
    assert need.issubset(df.columns)
    assert df["fraud_score"].between(0, 1).all()
    assert df["anomaly_score"].between(0, 1).all()
    assert set(df["payment_action"].unique()) <= {"approve", "step_up", "review", "block"}
    assert (df["expected_fraud_loss"] >= 0).all()

    s = json.load(open(config.OUTPUTS / "fraud_policy_summary.json"))
    for k in [
        "pr_auc", "precision", "recall", "fraud_capture_rate",
        "false_positive_rate", "false_negative_rate",
        "manual_review_volume", "action_mix", "threshold_tradeoff",
    ]:
        assert k in s, f"Missing key in summary: {k}"

    # capacity respected
    assert s["manual_review_volume"] <= config.MANUAL_REVIEW_CAPACITY

    aj = json.load(open(config.OUTPUTS / "fraud_alerts.json"))
    assert aj["is_sample"] is True and aj["sample_size"] == len(aj["rows"])
