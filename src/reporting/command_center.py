"""Risk command center summary (doc 08 §5).

Assembles the portfolio-level dashboard KPIs from the already-written engine
outputs so every number traces to a backend file (no recomputation/divergence).
"""
import json

import pandas as pd

from src import config
from src.reporting.writers import write_json


def _load_json(name):
    with open(config.OUTPUTS / name) as f:
        return json.load(f)


def build() -> dict:
    dec = pd.read_csv(config.OUTPUTS / "underwriting_decisions.csv")
    uw_sum = _load_json("underwriting_policy_summary.json")
    el_sum = _load_json("expected_loss_summary.json")
    el_seg = _load_json("expected_loss_by_segment.json")
    fraud_sum = _load_json("fraud_policy_summary.json")
    verdicts = _load_json("model_risk_verdicts.json")
    vlist = verdicts if isinstance(verdicts, list) else verdicts.get("verdicts", verdicts)

    # highest-risk credit segment = risk grade with the highest expected-loss rate
    grade_segs = el_seg["credit_segments"]["risk_grade"]
    highest = max(grade_segs, key=lambda r: r["expected_loss_rate"])

    verdict_counts = {}
    for v in vlist:
        verdict_counts[v["validation_verdict"]] = verdict_counts.get(v["validation_verdict"], 0) + 1

    summary = {
        "total_applicants": int(len(dec)),
        "approval_rate": uw_sum["approval_rate"],
        "review_rate": uw_sum["review_rate"],
        "decline_rate": uw_sum["decline_rate"],
        "average_PD": round(float(dec["PD"].mean()), 6),
        "total_approved_exposure": el_sum["total_approved_exposure"],
        "total_expected_credit_loss": el_sum["total_expected_credit_loss"],
        "total_expected_fraud_loss": el_sum["total_expected_fraud_loss"],
        "stablecoin_risk_exposure": el_sum["total_stablecoin_risk_exposure"],
        "manual_review_volume": fraud_sum["manual_review_volume"],
        "model_verdict_summary": {
            "by_model": {v["model_name"]: v["validation_verdict"] for v in vlist},
            "counts": verdict_counts,
        },
        "highest_risk_segment": {
            "dimension": "risk_grade",
            "segment": highest["risk_grade"],
            "expected_loss_rate": highest["expected_loss_rate"],
            "total_expected_loss": highest["total_expected_loss"],
        },
        "data_disclaimer": "Hybrid data: real LendingClub/Kaggle/FRED inputs plus clearly-labeled synthetic stablecoin and synthetic payment-context features. Estimates are modeled, not realized; default_flag is a default/severe-delinquency proxy.",
    }
    write_json(config.OUTPUTS / "risk_command_center.json", summary)
    return summary
