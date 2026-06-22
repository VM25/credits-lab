"""Reconciliation + required-output gates (doc 08 §15, doc 11 §11).

Hard gates run at the end of the pipeline:
* required_outputs(): every canonical output file exists and is non-empty.
* totals(): cross-file totals reconcile and verdicts are present/consistent.
Either raises and halts the build.
"""
import json

import pandas as pd

from src import config


class MissingOutputError(Exception):
    """Raised when a required output file is missing or empty."""


class ReconciliationError(Exception):
    """Raised when cross-file totals or verdicts do not reconcile."""


REQUIRED_CSVS = [
    "underwriting_decisions.csv", "fraud_alerts.csv", "stablecoin_alerts.csv",
    "expected_loss_applicant_level.csv", "credit_model_validation.csv",
    "fraud_model_validation.csv", "stablecoin_model_validation.csv",
    "policy_threshold_grid.csv", "data_quality_report.csv",
]
REQUIRED_JSONS = [
    "risk_command_center.json", "underwriting_decisions.json",
    "underwriting_policy_summary.json", "fraud_alerts.json", "stablecoin_alerts.json",
    "fraud_policy_summary.json", "expected_loss_summary.json",
    "expected_loss_by_segment.json", "stress_loss_summary.json",
    "policy_loss_comparison.json", "policy_simulator_inputs.json",
    "policy_simulator_results.json", "model_validation_summary.json",
    "champion_challenger_comparison.json", "model_risk_verdicts.json",
    "methodology_summary.json",
]
REQUIRED_PROCESSED = [
    "processed_credit_applicants.csv", "processed_payment_transactions.csv",
    "processed_stablecoin_transactions.csv", "macro_stress_inputs.csv",
    "underwriting_model_dataset.csv", "fraud_model_dataset.csv", "validation_dataset.csv",
]
# Files the contract forbids (chart data must be embedded, not standalone)
FORBIDDEN_OUTPUTS = ["calibration_curve.json", "decile_default_table.csv"]


def required_outputs() -> dict:
    """Assert all 9 CSV + 16 JSON outputs (+ 7 processed) exist and are non-empty."""
    missing, empty = [], []
    for name in REQUIRED_CSVS + REQUIRED_JSONS:
        p = config.OUTPUTS / name
        if not p.exists():
            missing.append(name)
        elif p.stat().st_size == 0:
            empty.append(name)
    for name in REQUIRED_PROCESSED:
        p = config.PROCESSED / name
        if not p.exists():
            missing.append(f"processed/{name}")
        elif p.stat().st_size == 0:
            empty.append(f"processed/{name}")
    extra = [f for f in FORBIDDEN_OUTPUTS if (config.OUTPUTS / f).exists()]
    if missing or empty or extra:
        raise MissingOutputError(
            f"missing={missing} empty={empty} forbidden_present={extra}")
    return {"csv": len(REQUIRED_CSVS), "json": len(REQUIRED_JSONS),
            "processed": len(REQUIRED_PROCESSED)}


def _load(name):
    with open(config.OUTPUTS / name) as f:
        return json.load(f)


def totals() -> dict:
    """Cross-file reconciliation (doc 08 §15). Raises ReconciliationError on mismatch."""
    dec = pd.read_csv(config.OUTPUTS / "underwriting_decisions.csv")
    app = pd.read_csv(config.OUTPUTS / "expected_loss_applicant_level.csv")
    cc = _load("risk_command_center.json")
    el = _load("expected_loss_summary.json")

    # 1. applicant counts reconcile across files
    if not (len(dec) == len(app) == cc["total_applicants"]):
        raise ReconciliationError(
            f"applicant counts differ: decisions={len(dec)} el={len(app)} cc={cc['total_applicants']}")

    # 2. command center credit loss == expected-loss summary credit loss
    if abs(cc["total_expected_credit_loss"] - el["total_expected_credit_loss"]) > 0.5:
        raise ReconciliationError("command-center credit loss != expected_loss_summary")

    # 3. applicant-level EL sum reconciles to the portfolio total (within rounding)
    el_sum_rows = round(float(app["expected_loss"].sum()), 2)
    if abs(el_sum_rows - el["total_expected_credit_loss"]) > max(1.0, 1e-6 * el["total_expected_credit_loss"]):
        raise ReconciliationError(
            f"applicant EL sum {el_sum_rows} != summary {el['total_expected_credit_loss']}")

    # 4. validation verdicts present for all 5 models and within the allowed set
    verdicts = _load("model_risk_verdicts.json")
    vlist = verdicts if isinstance(verdicts, list) else verdicts.get("verdicts", verdicts)
    if len(vlist) != 5:
        raise ReconciliationError(f"expected 5 model verdicts, got {len(vlist)}")
    if not all(v["validation_verdict"] in {"Pass", "Monitor", "Fail"} for v in vlist):
        raise ReconciliationError("invalid verdict value present")
    if not all(str(v.get("verdict_reason", "")).strip() for v in vlist):
        raise ReconciliationError("a verdict is missing its one-sentence reason")

    return {"applicants": int(len(dec)), "verdicts": len(vlist), "reconciled": True}
