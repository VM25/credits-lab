"""Data-quality and leakage gate.

Produces one report row per dataset (doc 08 section 11) and acts as a HARD STOP:
if any model dataset's canonical feature list contains a forbidden / label-derived
column, ``run()`` raises :class:`LeakageError` and the build halts.
"""
import numpy as np
import pandas as pd

from src import config
from src.data import features
from src.reporting.writers import write_csv

# Post-outcome credit fields that must never appear in the underwriting model.
CREDIT_FORBIDDEN = {
    "recoveries", "collection_recovery_fee", "total_pymnt", "total_rec_prncp",
    "total_rec_int", "last_pymnt_d", "last_pymnt_amnt", "out_prncp",
    "next_pymnt_d", "loan_status",
}
# Label-derived fraud fields that must never appear in the fraud model features.
FRAUD_FORBIDDEN = {"fraud_flag", "chargeback_loss"}

_REPORT_COLUMNS = [
    "dataset_name", "row_count", "column_count", "missing_value_count",
    "duplicate_id_count", "target_rate", "date_min", "date_max",
    "leakage_check_status", "schema_check_status",
]


class LeakageError(Exception):
    """Raised when a forbidden / label-derived column leaks into a model feature list."""


def _date_bounds(df, date_col):
    if date_col is None or date_col not in df.columns:
        return None, None
    d = pd.to_datetime(df[date_col], errors="coerce")
    if d.notna().any():
        return str(d.min().date()), str(d.max().date())
    return None, None


def _target_rate(df, target_col):
    if target_col is None or target_col not in df.columns:
        return np.nan
    s = pd.to_numeric(df[target_col], errors="coerce")
    return float(s.mean()) if s.notna().any() else np.nan


def _dup_id_count(df, id_col):
    if id_col is None or id_col not in df.columns:
        return 0
    return int(df[id_col].duplicated().sum())


def run():
    """Build the data-quality report, write it to outputs, and enforce the leakage gate.

    Returns the report DataFrame. Raises :class:`LeakageError` if any model
    dataset's feature list contains a forbidden column.
    """
    # Ensure model datasets and canonical feature lists are current.
    uw, fr, val = features.run()

    raw_credit = pd.read_csv(config.PROCESSED / "processed_credit_applicants.csv")
    raw_pay = pd.read_csv(config.PROCESSED / "processed_payment_transactions.csv")
    raw_stable = pd.read_csv(config.PROCESSED / "processed_stablecoin_transactions.csv")
    raw_macro = pd.read_csv(config.PROCESSED / "macro_stress_inputs.csv")

    uw_features = set(features.UNDERWRITING_FEATURES)
    fr_features = set(features.FRAUD_FEATURES)

    # --- leakage checks (compute status; raise at the end if any fail) ---
    leakage_failures = []

    def _uw_leakage_status():
        bad = (CREDIT_FORBIDDEN & uw_features) | ({"default_flag", "loss_amount_if_default"} & uw_features)
        if bad:
            leakage_failures.append(f"underwriting features contain forbidden columns: {sorted(bad)}")
            return "fail"
        return "pass"

    def _fraud_leakage_status():
        bad = FRAUD_FORBIDDEN & fr_features
        if bad:
            leakage_failures.append(f"fraud features contain forbidden columns: {sorted(bad)}")
            return "fail"
        return "pass"

    uw_leak = _uw_leakage_status()
    fr_leak = _fraud_leakage_status()
    val_leak = uw_leak  # validation shares the underwriting feature contract

    # --- schema checks ---
    def _schema_status(df, required):
        return "pass" if set(required).issubset(df.columns) else "fail"

    rows = []

    # processed_credit_applicants (raw source)
    dmin, dmax = _date_bounds(raw_credit, "application_date")
    rows.append({
        "dataset_name": "processed_credit_applicants",
        "row_count": len(raw_credit),
        "column_count": raw_credit.shape[1],
        "missing_value_count": int(raw_credit.isna().sum().sum()),
        "duplicate_id_count": _dup_id_count(raw_credit, "applicant_id"),
        "target_rate": _target_rate(raw_credit, "default_flag"),
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": "pass",
        "schema_check_status": _schema_status(
            raw_credit, ["applicant_id", "application_date", "default_flag"]),
    })

    # processed_payment_transactions (raw source)
    dmin, dmax = _date_bounds(raw_pay, "transaction_time")
    rows.append({
        "dataset_name": "processed_payment_transactions",
        "row_count": len(raw_pay),
        "column_count": raw_pay.shape[1],
        "missing_value_count": int(raw_pay.isna().sum().sum()),
        "duplicate_id_count": _dup_id_count(raw_pay, "transaction_id"),
        "target_rate": _target_rate(raw_pay, "fraud_flag"),
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": "pass",
        "schema_check_status": _schema_status(
            raw_pay, ["transaction_id", "transaction_time", "fraud_flag"]),
    })

    # processed_stablecoin_transactions (raw source)
    dmin, dmax = _date_bounds(raw_stable, "transaction_time")
    rows.append({
        "dataset_name": "processed_stablecoin_transactions",
        "row_count": len(raw_stable),
        "column_count": raw_stable.shape[1],
        "missing_value_count": int(raw_stable.isna().sum().sum()),
        "duplicate_id_count": _dup_id_count(raw_stable, "wallet_id"),
        "target_rate": _target_rate(raw_stable, "stablecoin_risk_label"),
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": "pass",
        "schema_check_status": _schema_status(
            raw_stable, ["wallet_id", "transaction_time", "stablecoin_risk_label"]),
    })

    # macro_stress_inputs (raw source; no id / no target)
    dmin, dmax = _date_bounds(raw_macro, "date")
    rows.append({
        "dataset_name": "macro_stress_inputs",
        "row_count": len(raw_macro),
        "column_count": raw_macro.shape[1],
        "missing_value_count": int(raw_macro.isna().sum().sum()),
        "duplicate_id_count": np.nan,
        "target_rate": np.nan,
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": "pass",
        "schema_check_status": _schema_status(raw_macro, ["date"]),
    })

    # underwriting_model_dataset (model dataset)
    dmin, dmax = _date_bounds(uw, "application_date")
    rows.append({
        "dataset_name": "underwriting_model_dataset",
        "row_count": len(uw),
        "column_count": uw.shape[1],
        "missing_value_count": int(uw.isna().sum().sum()),
        "duplicate_id_count": _dup_id_count(uw, "applicant_id"),
        "target_rate": _target_rate(uw, "default_flag"),
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": uw_leak,
        "schema_check_status": _schema_status(
            uw, ["applicant_id", "default_flag", "split"]),
    })

    # fraud_model_dataset (model dataset)
    dmin, dmax = _date_bounds(fr, "transaction_time")
    rows.append({
        "dataset_name": "fraud_model_dataset",
        "row_count": len(fr),
        "column_count": fr.shape[1],
        "missing_value_count": int(fr.isna().sum().sum()),
        "duplicate_id_count": _dup_id_count(fr, "transaction_id"),
        "target_rate": _target_rate(fr, "fraud_flag"),
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": fr_leak,
        "schema_check_status": _schema_status(
            fr, ["transaction_id", "fraud_flag", "split"]),
    })

    # validation_dataset (held-out underwriting rows)
    dmin, dmax = _date_bounds(val, "application_date")
    rows.append({
        "dataset_name": "validation_dataset",
        "row_count": len(val),
        "column_count": val.shape[1],
        "missing_value_count": int(val.isna().sum().sum()),
        "duplicate_id_count": _dup_id_count(val, "applicant_id"),
        "target_rate": _target_rate(val, "default_flag"),
        "date_min": dmin, "date_max": dmax,
        "leakage_check_status": val_leak,
        "schema_check_status": _schema_status(
            val, ["applicant_id", "default_flag", "split"]),
    })

    report = pd.DataFrame(rows, columns=_REPORT_COLUMNS)
    write_csv(config.OUTPUTS / "data_quality_report.csv", report)

    # HARD STOP: fail the build if any leakage check failed.
    if leakage_failures:
        raise LeakageError("; ".join(leakage_failures))

    return report
