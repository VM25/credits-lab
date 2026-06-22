import json

from src import config
from src.reporting import command_center, methodology


def test_command_center():
    cc = command_center.build()
    for k in ["total_applicants", "approval_rate", "review_rate", "decline_rate", "average_PD",
              "total_approved_exposure", "total_expected_credit_loss", "total_expected_fraud_loss",
              "stablecoin_risk_exposure", "manual_review_volume", "model_verdict_summary",
              "highest_risk_segment"]:
        assert k in cc
    assert (config.OUTPUTS / "risk_command_center.json").exists()
    assert 0 <= cc["approval_rate"] <= 1
    assert cc["model_verdict_summary"]["counts"]  # non-empty verdict counts


def test_methodology_keys_and_no_forbidden_copy():
    m = methodology.build()
    for k in ["data_sources", "synthetic_data_disclosure", "model_list", "feature_summary",
              "split_method", "loss_assumptions", "stress_assumptions", "validation_methods",
              "known_limitations", "default_flag_definition", "chart_data_embedding_map"]:
        assert k in m
    blob = json.dumps(m).lower()
    for term in ["production-ready", "institutional-grade", "aml compliance",
                 "guaranteed fraud", "real-time bank", "optimal credit policy", "ai-powered magic"]:
        assert term not in blob, term
