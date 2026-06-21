"""Feature engineering and model-dataset construction.

Builds three deterministic model datasets from the processed sources:

* ``underwriting_model_dataset.csv`` - ACCEPTED applicants only, application-time
  predictors plus a time-aware ``split`` column.
* ``fraud_model_dataset.csv`` - all payment rows with engineered behavioural
  features; ``fraud_flag`` and ``chargeback_loss`` are kept as columns (target /
  expected-loss inputs) but are deliberately EXCLUDED from ``FRAUD_FEATURES``.
* ``validation_dataset.csv`` - the held-out (val + test) underwriting rows used
  downstream for calibration and the final, untouched test.

``UNDERWRITING_FEATURES`` and ``FRAUD_FEATURES`` are the canonical predictor
lists consumed by the modelling and leakage-gate code. They MUST NOT contain any
label-derived column (the core leakage guard).
"""
import numpy as np
import pandas as pd

from src import config
from src.data import splits
from src.reporting.writers import write_csv

# --- canonical predictor lists (populated by run()) --------------------------
# Application-time numeric / encoded predictors for the underwriting model.
UNDERWRITING_FEATURES = []
# V1..V28 + engineered behavioural features for the fraud model.
FRAUD_FEATURES = []

_CREDIT_GRADE_MAP = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
_UTIL_BAND_MAP = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
_MERCHANT_RISK_MAP = {"low": 0.2, "medium": 0.5, "high": 0.8}


def _safe_ratio(numer, denom):
    """Element-wise numer/denom; divide-by-zero or non-finite -> NaN."""
    out = numer / denom.replace({0: np.nan})
    return out.replace([np.inf, -np.inf], np.nan)


def _build_underwriting(credit: pd.DataFrame):
    """Return (dataframe, feature_list) for the accepted-applicant underwriting model."""
    # Accepted only: target must be populated.
    uw = credit[credit["applicant_type"] == "accepted"].copy()
    uw = uw[uw["default_flag"].notna()].reset_index(drop=True)

    # Engineered features (spec doc 02 section 4).
    uw["income_to_loan_ratio"] = _safe_ratio(uw["annual_income"], uw["loan_amount"])
    uw["debt_burden_score"] = uw["debt_to_income"] / 100.0
    uw["credit_utilization_band"] = pd.cut(
        uw["revolving_utilization"],
        bins=[-np.inf, 30.0, 60.0, 90.0, np.inf],
        labels=["low", "medium", "high", "very_high"],
    ).astype(object)
    uw["loan_size_band"] = pd.qcut(
        uw["loan_amount"], q=4, labels=["q1", "q2", "q3", "q4"], duplicates="drop"
    ).astype(object)
    uw["credit_grade_numeric"] = uw["credit_grade"].map(_CREDIT_GRADE_MAP)
    uw["prior_delinquency_flag"] = (uw["delinquency_history"].fillna(0) > 0).astype(int)
    uw["application_vintage"] = pd.to_datetime(
        uw["application_date"], errors="coerce"
    ).dt.year

    # Ordinal encodings of the bands (kept alongside the readable band labels).
    uw["credit_utilization_band_ord"] = uw["credit_utilization_band"].map(_UTIL_BAND_MAP)
    _loan_size_ord_map = {"q1": 0, "q2": 1, "q3": 2, "q4": 3}
    uw["loan_size_band_ord"] = uw["loan_size_band"].map(_loan_size_ord_map)

    # One-hot encode home_ownership (low cardinality). loan_purpose has ~135
    # categories, so we drop it rather than explode the feature space.
    home_dummies = pd.get_dummies(
        uw["home_ownership"].fillna("UNKNOWN"), prefix="home", dtype=int
    )
    home_dummies = home_dummies.reindex(sorted(home_dummies.columns), axis=1)
    uw = pd.concat([uw, home_dummies], axis=1)

    # Time-aware split on application_date.
    sp = splits.time_split(uw, "application_date")
    uw["split"] = ""
    for name, idx in sp.items():
        uw.loc[idx, "split"] = name

    # Canonical predictor list: numeric / encoded application-time fields ONLY.
    # EXCLUDES: ids, dates, target (default_flag), loss_amount_if_default
    # (deterministic loan_amount*LGD - redundant/label-derived), applicant_type,
    # is_synthetic_reject, split, and raw categoricals (credit_grade, home_ownership,
    # loan_purpose, the readable band labels).
    feature_list = [
        "loan_amount",
        "annual_income",
        "debt_to_income",
        "employment_length",
        "interest_rate",
        "delinquency_history",
        "revolving_utilization",
        "open_accounts",
        "income_to_loan_ratio",
        "debt_burden_score",
        "credit_grade_numeric",
        "prior_delinquency_flag",
        "application_vintage",
        "credit_utilization_band_ord",
        "loan_size_band_ord",
    ] + list(home_dummies.columns)

    return uw, feature_list


def _build_fraud(pay: pd.DataFrame):
    """Return (dataframe, feature_list) for the payment-fraud model."""
    fr = pay.copy()
    fr["transaction_time"] = pd.to_datetime(fr["transaction_time"], errors="coerce")
    # Stable order by account then time so windowed features have no lookahead.
    fr = fr.sort_values(["account_id", "transaction_time"], kind="stable").reset_index(drop=True)

    # --- prior-window velocities (strictly past transactions per account) ---
    def _prior_window_count(group, window):
        times = group["transaction_time"]
        counts = np.zeros(len(group), dtype=int)
        # Two-pointer over time-ordered transactions; count strictly-prior rows
        # whose timestamp is within `window` of the current row.
        start = 0
        for i in range(len(group)):
            t_i = times.iloc[i]
            while times.iloc[start] < t_i - window:
                start += 1
            counts[i] = i - start  # rows in [start, i) -> strictly prior, in-window
        return pd.Series(counts, index=group.index)

    one_hour = pd.Timedelta(hours=1)
    one_day = pd.Timedelta(hours=24)
    fr["velocity_1h"] = fr.groupby("account_id", group_keys=False).apply(
        lambda g: _prior_window_count(g, one_hour), include_groups=False
    )
    fr["velocity_24h"] = fr.groupby("account_id", group_keys=False).apply(
        lambda g: _prior_window_count(g, one_day), include_groups=False
    )

    # --- per-account amount z-score (std==0 -> 0) ---
    grp = fr.groupby("account_id")["amount"]
    acct_mean = grp.transform("mean")
    acct_std = grp.transform("std").fillna(0.0)
    z = (fr["amount"] - acct_mean) / acct_std.replace({0: np.nan})
    fr["amount_zscore_by_account"] = z.fillna(0.0)

    # --- merchant risk score from band ---
    fr["merchant_risk_score"] = fr["merchant_risk_band"].map(_MERCHANT_RISK_MAP).fillna(0.5)

    # --- first-occurrence flags per account (time-ordered) ---
    fr["new_device_flag"] = (
        (~fr.duplicated(subset=["account_id", "device_proxy"], keep="first")).astype(int)
    )
    fr["new_location_flag"] = (
        (~fr.duplicated(subset=["account_id", "location_proxy"], keep="first")).astype(int)
    )

    # --- temporal / amount flags ---
    fr["night_transaction_flag"] = fr["transaction_time"].dt.hour.between(0, 5).astype(int)
    high_thresh = fr["amount"].quantile(0.99)
    fr["high_amount_flag"] = (fr["amount"] > high_thresh).astype(int)

    # --- account tenure band ---
    fr["account_tenure_band"] = pd.cut(
        fr["account_age_days"],
        bins=[-np.inf, 90, 365, 1095, np.inf],
        labels=["new", "established", "mature", "veteran"],
    ).astype(object)
    _tenure_ord = {"new": 0, "established": 1, "mature": 2, "veteran": 3}
    fr["account_tenure_band_ord"] = fr["account_tenure_band"].map(_tenure_ord)

    # Time-aware split on transaction_time.
    sp = splits.time_split(fr, "transaction_time")
    fr["split"] = ""
    for name, idx in sp.items():
        fr.loc[idx, "split"] = name

    # Canonical predictor list. LEAKAGE-CRITICAL: NEVER include fraud_flag (target)
    # or chargeback_loss (label-derived). Also excludes ids, transaction_time,
    # is_synthetic_context, split, and raw categoricals.
    v_cols = [f"V{i}" for i in range(1, 29)]
    feature_list = v_cols + [
        "amount",
        "account_age_days",
        "transaction_count_24h",
        "amount_count_24h",
        "velocity_1h",
        "velocity_24h",
        "amount_zscore_by_account",
        "merchant_risk_score",
        "new_device_flag",
        "new_location_flag",
        "night_transaction_flag",
        "high_amount_flag",
        "account_tenure_band_ord",
    ]

    return fr, feature_list


def run():
    """Build and persist the three model datasets; return ``(uw, fr, val)``.

    Also (re)populates module-level ``UNDERWRITING_FEATURES`` and
    ``FRAUD_FEATURES`` with the canonical predictor lists.
    """
    global UNDERWRITING_FEATURES, FRAUD_FEATURES

    credit = pd.read_csv(config.PROCESSED / "processed_credit_applicants.csv")
    pay = pd.read_csv(config.PROCESSED / "processed_payment_transactions.csv")

    uw, uw_features = _build_underwriting(credit)
    fr, fr_features = _build_fraud(pay)

    UNDERWRITING_FEATURES = uw_features
    FRAUD_FEATURES = fr_features

    # Validation dataset: held-out underwriting rows (val + test).
    val = uw[uw["split"].isin(["val", "test"])].reset_index(drop=True)

    write_csv(config.PROCESSED / "underwriting_model_dataset.csv", uw)
    write_csv(config.PROCESSED / "fraud_model_dataset.csv", fr)
    write_csv(config.PROCESSED / "validation_dataset.csv", val)

    return uw, fr, val
