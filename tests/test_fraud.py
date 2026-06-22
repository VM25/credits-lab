from src.risk import fraud
from src import config


def test_action_bands():
    assert fraud.action(0.30) == "approve" and fraud.action(0.45) == "step_up"
    assert fraud.action(0.70) == "review" and fraud.action(0.90) == "block"


def test_expected_fraud_loss():
    assert fraud.expected_fraud_loss(0.5, 100) == 0.5 * 100 * config.FRAUD_LOSS_SEVERITY
    assert fraud.expected_fraud_loss(0.0, 100) == 0.0
