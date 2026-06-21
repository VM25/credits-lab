"""Underwriting engine — Tasks 3.2 (policy helpers) + 3.3 (output builder).

Policy helpers
--------------
risk_grade(pd_value)          -> str  "A".."E"
decision(pd_value)            -> str  "approve" | "review" | "decline"
lgd_for(risk_grade)           -> float
ead_for(loan_amount)          -> float
recommended_limit(row)        -> float  (heuristic, labeled as such)
ALLOWED_REASONS               dict   reason_code -> human-readable explanation
reason_codes(row)             -> list[str]  top 1-3 triggered reason codes

Output builder
--------------
build()                       -> dict  summary; also writes the 3 output files
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.data.features import underwriting_features
from src.models import calibration, gbm, scorecard
from src.models.metrics import brier as _brier, roc_auc as _roc_auc
from src.reporting.writers import write_csv, write_json

# ---------------------------------------------------------------------------
# Task 3.2 — pure policy helpers
# ---------------------------------------------------------------------------

def risk_grade(pd_value: float) -> str:
    """Map a PD value to a risk grade A..E using config.RISK_GRADE_BANDS."""
    for grade, upper in config.RISK_GRADE_BANDS:
        if pd_value < upper:
            return grade
    # Fallback: return last grade (E) for pd == upper bound of last band
    return config.RISK_GRADE_BANDS[-1][0]


def decision(pd_value: float) -> str:
    """Return 'approve', 'review', or 'decline' based on PD vs config thresholds."""
    if pd_value < config.PD_APPROVE:
        return "approve"
    if pd_value < config.PD_DECLINE:
        return "review"
    return "decline"


def lgd_for(grade: str) -> float:
    """Return LGD assumption for a risk grade.

    A, B -> LGD_BY_RISK["low"]
    C, D -> LGD_BY_RISK["standard"]
    E    -> LGD_BY_RISK["high"]

    This is the single source of LGD-by-grade; the Phase-6 expected-loss
    engine should import this function.
    """
    if grade in ("A", "B"):
        return config.LGD_BY_RISK["low"]
    if grade in ("C", "D"):
        return config.LGD_BY_RISK["standard"]
    # grade == "E" (or any unknown)
    return config.LGD_BY_RISK["high"]


def ead_for(loan_amount: float) -> float:
    """Exposure at Default for installment loans = loan_amount (non-negative)."""
    return max(0.0, float(loan_amount))


def recommended_limit(row) -> float:
    """Heuristic credit-limit recommendation based on income, PD, and DTI.

    NOTE: This is a labeled heuristic rule, NOT an institutional credit-line
    model. It is designed for demonstration purposes only.

    Logic
    -----
    base   = annual_income * 0.30
    pd_scaler  = (1 - PD)           — lower PD → higher limit
    dti_factor = clip(1 - debt_to_income/100, 0.10, 1.0)
    limit  = base * pd_scaler * dti_factor  (floored at 0, rounded to 2 dp)
    """
    annual_income = float(row.get("annual_income", 0) or 0)
    pd_val = float(row.get("PD", 0) or 0)
    dti = float(row.get("debt_to_income", 0) or 0)

    base = annual_income * 0.30
    pd_scaler = max(0.0, 1.0 - pd_val)
    dti_factor = float(np.clip(1.0 - dti / 100.0, 0.10, 1.0))
    limit = base * pd_scaler * dti_factor
    return float(max(0.0, round(limit, 2)))


# ---------------------------------------------------------------------------
# Reason-code registry (doc 03 §10)
# ---------------------------------------------------------------------------

ALLOWED_REASONS: dict[str, str] = {
    "high_debt_to_income": (
        "Debt-to-income ratio exceeds the acceptable threshold, indicating "
        "a high existing debt burden relative to income."
    ),
    "low_income_to_loan_coverage": (
        "Annual income is insufficient relative to the requested loan amount, "
        "reducing confidence in repayment capacity."
    ),
    "high_revolving_utilization": (
        "Revolving credit utilization is elevated, suggesting the applicant "
        "is using a high proportion of available credit."
    ),
    "prior_delinquency": (
        "Prior delinquency history has been recorded on this account, "
        "indicating past difficulty meeting payment obligations."
    ),
    "weak_credit_grade": (
        "The applicant's credit grade falls within a higher-risk band, "
        "reflecting elevated credit risk based on bureau data."
    ),
    "large_loan_amount": (
        "The requested loan amount is in the upper quartile relative to "
        "the applicant population, representing elevated exposure."
    ),
    "high_predicted_default_risk": (
        "The model-estimated probability of default exceeds the decline "
        "threshold based on the applicant's financial profile."
    ),
}

# Severity ordering for prioritising which codes to surface (most severe first).
_REASON_SEVERITY_ORDER = [
    "high_predicted_default_risk",
    "prior_delinquency",
    "high_debt_to_income",
    "weak_credit_grade",
    "high_revolving_utilization",
    "low_income_to_loan_coverage",
    "large_loan_amount",
]

def reason_codes(row, large_loan_threshold: float = 25000.0) -> list[str]:
    """Return the top 1–3 triggered reason codes for an applicant row.

    Codes are ordered by severity (most severe first). All codes are keys
    of ALLOWED_REASONS — never opaque 'model says risky' phrasing.

    Parameters
    ----------
    row : dict-like applicant row (must support .get())
    large_loan_threshold : loan_amount Q3 from the accepted-book train split.
        Defaults to 25000.0 as a sensible standalone fallback.

    Triggers
    --------
    high_debt_to_income          : debt_to_income > 35
    low_income_to_loan_coverage  : income_to_loan_ratio < 1.0
    high_revolving_utilization   : revolving_utilization > 80
    prior_delinquency            : prior_delinquency_flag == 1
    weak_credit_grade            : credit_grade in {E,F,G} or credit_grade_numeric >= 5
    large_loan_amount            : loan_amount >= large_loan_threshold (top quartile)
    high_predicted_default_risk  : PD >= config.PD_DECLINE
    """
    triggered: list[str] = []

    dti = float(row.get("debt_to_income") or 0)
    income_to_loan = float(row.get("income_to_loan_ratio") or 0)
    rev_util = float(row.get("revolving_utilization") or 0)
    prior_delinq = int(row.get("prior_delinquency_flag") or 0)
    credit_grade_str = str(row.get("credit_grade") or "")
    credit_grade_num = float(row.get("credit_grade_numeric") or 0)
    loan_amount = float(row.get("loan_amount") or 0)
    pd_val = float(row.get("PD") or 0)

    if pd_val >= config.PD_DECLINE:
        triggered.append("high_predicted_default_risk")
    if prior_delinq == 1:
        triggered.append("prior_delinquency")
    if dti > 35:
        triggered.append("high_debt_to_income")
    if credit_grade_str.upper() in ("E", "F", "G") or credit_grade_num >= 5:
        triggered.append("weak_credit_grade")
    if rev_util > 80:
        triggered.append("high_revolving_utilization")
    if income_to_loan < 1.0:
        triggered.append("low_income_to_loan_coverage")
    if loan_amount >= large_loan_threshold:
        triggered.append("large_loan_amount")

    # Deduplicate while preserving severity order.
    seen: set[str] = set()
    ordered: list[str] = []
    for code in _REASON_SEVERITY_ORDER:
        if code in triggered and code not in seen:
            ordered.append(code)
            seen.add(code)

    return ordered[:3]


# ---------------------------------------------------------------------------
# Task 3.3 — output builder
# ---------------------------------------------------------------------------

def build() -> dict:
    """Train models, compute decisions, write outputs, return summary dict.

    Steps
    -----
    1. Load underwriting_model_dataset; split by 'split' column.
    2. Impute predictor NaNs with TRAIN medians.
    3. Fit champion (scorecard) + challenger (GBM) on train.
    4. Calibrate champion on val. Use calibrated PD for all decisions.
    5. Compute per-row: PD, risk_grade, decision, LGD, EAD, EL, limit,
       reason_codes.
    6. Write underwriting_decisions.csv (all rows).
    7. Write underwriting_decisions.json (stratified sample ≤ UI_SAMPLE_ROWS).
    8. Write underwriting_policy_summary.json (aggregates over all rows).

    Returns
    -------
    dict with key summary stats.
    """
    # ------------------------------------------------------------------
    # 1. Load dataset and split
    # ------------------------------------------------------------------
    df = pd.read_csv(config.PROCESSED / "underwriting_model_dataset.csv")

    train = df[df["split"] == "train"].copy()
    val = df[df["split"] == "val"].copy()
    test = df[df["split"] == "test"].copy()

    feat_names = underwriting_features(df)

    # ------------------------------------------------------------------
    # 2. Impute NaNs with TRAIN medians (computed once, applied to all)
    # ------------------------------------------------------------------
    train_medians: dict[str, float] = {
        col: float(train[col].median()) for col in feat_names
    }
    for col, med in train_medians.items():
        train[col] = train[col].fillna(med)
        val[col] = val[col].fillna(med)
        test[col] = test[col].fillna(med)
        df[col] = df[col].fillna(med)

    # Loan-amount Q3 threshold from train — passed explicitly to reason_codes
    loan_amount_q3 = float(train["loan_amount"].quantile(0.75))

    X_train = train[feat_names].values
    y_train = train["default_flag"].values
    X_val = val[feat_names].values
    y_val = val["default_flag"].values
    X_test = test[feat_names].values
    y_test = test["default_flag"].values
    X_all = df[feat_names].values

    # ------------------------------------------------------------------
    # 3. Fit champion (logistic scorecard) + challenger (GBM)
    # ------------------------------------------------------------------
    champion = scorecard.fit(X_train, y_train, feature_names=feat_names)
    challenger = gbm.fit(X_train, y_train, feature_names=feat_names)

    # ------------------------------------------------------------------
    # 4. Calibrate champion AND challenger on VAL;
    #    champion calibrated PD drives all decisions (unchanged).
    # ------------------------------------------------------------------
    val_raw_scores_champ = champion.predict_proba(X_val)
    calibrator = calibration.fit(val_raw_scores_champ, y_val)

    val_raw_scores_chall = challenger.predict_proba(X_val)
    challenger_calibrator = calibration.fit(val_raw_scores_chall, y_val)

    # Calibrated PD for all rows (champion drives decisions)
    all_raw_scores = champion.predict_proba(X_all)
    all_pd = calibrator.transform(all_raw_scores)  # clipped [0,1]

    # Champion and challenger calibrated PD on the held-out TEST split
    test_champ_pd = calibrator.transform(champion.predict_proba(X_test))
    test_chall_pd = challenger_calibrator.transform(challenger.predict_proba(X_test))

    # ------------------------------------------------------------------
    # 5. Per-row computation
    # ------------------------------------------------------------------
    records = []
    for i, (idx, row) in enumerate(df.iterrows()):
        pd_val = float(all_pd[i])
        grade = risk_grade(pd_val)
        dec = decision(pd_val)
        lgd = lgd_for(grade)
        loan_amount = float(row["loan_amount"])
        ead = ead_for(loan_amount)
        el = pd_val * lgd * ead
        el_rate = el / ead if ead > 0 else 0.0

        # Enrich row dict with PD for reason_codes (uses .get())
        row_dict = row.to_dict()
        row_dict["PD"] = pd_val

        # recommended_limit also needs PD in the row dict
        limit = recommended_limit(row_dict)

        codes = reason_codes(row_dict, large_loan_threshold=loan_amount_q3)
        # Pad to 3 with empty strings
        while len(codes) < 3:
            codes.append("")

        records.append({
            "applicant_id": row["applicant_id"],
            "PD": pd_val,
            "risk_grade": grade,
            "decision": dec,
            "recommended_credit_limit": limit,
            "LGD": lgd,
            "EAD": ead,
            "expected_loss": el,
            "expected_loss_rate": el_rate,
            "top_reason_1": codes[0],
            "top_reason_2": codes[1],
            "top_reason_3": codes[2],
            "model_used": "champion_logistic_scorecard",
        })

    decisions_df = pd.DataFrame(records)

    # Attach actual default_flag for policy summary (not written to decisions CSV)
    decisions_df["_actual_default"] = df["default_flag"].values

    # ------------------------------------------------------------------
    # 6. Write underwriting_decisions.csv (all rows, minus internal col)
    # ------------------------------------------------------------------
    csv_cols = [
        "applicant_id", "PD", "risk_grade", "decision",
        "recommended_credit_limit", "LGD", "EAD", "expected_loss",
        "expected_loss_rate", "top_reason_1", "top_reason_2", "top_reason_3",
        "model_used",
    ]
    write_csv(config.OUTPUTS / "underwriting_decisions.csv",
              decisions_df[csv_cols])

    # ------------------------------------------------------------------
    # 7. Write underwriting_decisions.json — stratified sample
    # ------------------------------------------------------------------
    total_rows = len(decisions_df)
    sample_size = min(config.UI_SAMPLE_ROWS, total_rows)

    # Stratified sample across decision categories
    decision_counts = decisions_df["decision"].value_counts()
    sampled_parts = []
    for dec_val, count in decision_counts.items():
        frac = count / total_rows
        n_from_dec = max(1, round(sample_size * frac))
        part = decisions_df[decisions_df["decision"] == dec_val]
        n_from_dec = min(n_from_dec, len(part))
        sampled_parts.append(
            part.sample(n=n_from_dec, random_state=config.SEED)
        )
    sample_df = pd.concat(sampled_parts).sample(
        frac=1, random_state=config.SEED
    ).reset_index(drop=True)

    # Trim/pad to exact sample_size
    sample_df = sample_df.iloc[:sample_size]
    actual_sample_size = len(sample_df)

    json_rows = sample_df[csv_cols].to_dict(orient="records")
    decisions_json = {
        "is_sample": True,
        "row_count_total": total_rows,
        "sample_size": actual_sample_size,
        "rows": json_rows,
    }
    write_json(config.OUTPUTS / "underwriting_decisions.json", decisions_json)

    # ------------------------------------------------------------------
    # 8. Write underwriting_policy_summary.json
    # ------------------------------------------------------------------
    # Rates (over all rows)
    n_total = len(decisions_df)
    n_approve = (decisions_df["decision"] == "approve").sum()
    n_review = (decisions_df["decision"] == "review").sum()
    n_decline = (decisions_df["decision"] == "decline").sum()

    approval_rate = float(n_approve / n_total)
    review_rate = float(n_review / n_total)
    decline_rate = float(n_decline / n_total)

    # Default rate by decision
    default_rate_by_decision: dict[str, float] = {}
    for dec_val in ["approve", "review", "decline"]:
        mask = decisions_df["decision"] == dec_val
        if mask.sum() > 0:
            default_rate_by_decision[dec_val] = float(
                decisions_df.loc[mask, "_actual_default"].mean()
            )
        else:
            default_rate_by_decision[dec_val] = None

    # Expected loss by decision
    expected_loss_by_decision: dict[str, float] = {}
    for dec_val in ["approve", "review", "decline"]:
        mask = decisions_df["decision"] == dec_val
        if mask.sum() > 0:
            expected_loss_by_decision[dec_val] = float(
                decisions_df.loc[mask, "expected_loss"].sum()
            )
        else:
            expected_loss_by_decision[dec_val] = 0.0

    # Average PD by decision
    average_pd_by_decision: dict[str, float] = {}
    for dec_val in ["approve", "review", "decline"]:
        mask = decisions_df["decision"] == dec_val
        if mask.sum() > 0:
            average_pd_by_decision[dec_val] = float(
                decisions_df.loc[mask, "PD"].mean()
            )
        else:
            average_pd_by_decision[dec_val] = None

    # PD distribution histogram
    pd_vals = decisions_df["PD"].values
    pd_counts, pd_edges = np.histogram(pd_vals, bins=20, range=(0.0, 1.0))
    pd_distribution = [
        {"bin_left": float(pd_edges[i]), "bin_right": float(pd_edges[i + 1]),
         "count": int(pd_counts[i])}
        for i in range(len(pd_counts))
    ]

    # Risk grade distribution
    risk_grade_distribution = decisions_df["risk_grade"].value_counts().to_dict()
    risk_grade_distribution = {k: int(v) for k, v in risk_grade_distribution.items()}

    # Approval mix
    approval_mix = decisions_df["decision"].value_counts().to_dict()
    approval_mix = {k: int(v) for k, v in approval_mix.items()}

    # Expected loss by risk grade
    el_by_grade = (
        decisions_df.groupby("risk_grade")["expected_loss"].sum().to_dict()
    )
    expected_loss_by_risk_grade = {k: float(v) for k, v in el_by_grade.items()}

    # Top decline reasons (count per reason code among declines)
    decline_mask = decisions_df["decision"] == "decline"
    decline_df = decisions_df[decline_mask]
    reason_counter: dict[str, int] = {}
    for col in ["top_reason_1", "top_reason_2", "top_reason_3"]:
        for code in decline_df[col]:
            if code and code in ALLOWED_REASONS:
                reason_counter[code] = reason_counter.get(code, 0) + 1
    top_decline_reasons = dict(
        sorted(reason_counter.items(), key=lambda x: -x[1])
    )

    # Champion calibration summary
    champion_calibration = {
        "brier_before": float(calibrator.brier_before),
        "brier_after": float(calibrator.brier_after),
    }

    # ------------------------------------------------------------------
    # Champion vs Challenger comparison on held-out TEST split (doc 03 §12)
    # ------------------------------------------------------------------
    # PD distributions on test (20-bin histogram, range [0, 1])
    def _pd_hist(pd_arr: np.ndarray) -> list[dict]:
        counts, edges = np.histogram(pd_arr, bins=20, range=(0.0, 1.0))
        return [
            {"bin_left": float(edges[i]), "bin_right": float(edges[i + 1]),
             "count": int(counts[i])}
            for i in range(len(counts))
        ]

    champ_roc = _roc_auc(y_test, test_champ_pd)
    champ_brier = _brier(y_test, test_champ_pd)
    chall_roc = _roc_auc(y_test, test_chall_pd)
    chall_brier = _brier(y_test, test_chall_pd)

    pd_corr = float(np.corrcoef(test_champ_pd, test_chall_pd)[0, 1])

    champion_vs_challenger = {
        "champion": {
            "roc_auc": float(champ_roc),
            "brier": float(champ_brier),
            "pd_distribution": _pd_hist(test_champ_pd),
        },
        "challenger": {
            "roc_auc": float(chall_roc),
            "brier": float(chall_brier),
            "pd_distribution": _pd_hist(test_chall_pd),
        },
        "pd_correlation": pd_corr,
    }

    policy_summary = {
        "approval_rate": approval_rate,
        "review_rate": review_rate,
        "decline_rate": decline_rate,
        "default_rate_by_decision": default_rate_by_decision,
        "expected_loss_by_decision": expected_loss_by_decision,
        "average_pd_by_decision": average_pd_by_decision,
        "pd_distribution": pd_distribution,
        "risk_grade_distribution": risk_grade_distribution,
        "approval_mix": approval_mix,
        "expected_loss_by_risk_grade": expected_loss_by_risk_grade,
        "top_decline_reasons": top_decline_reasons,
        "champion_calibration": champion_calibration,
        "champion_vs_challenger": champion_vs_challenger,
    }

    write_json(config.OUTPUTS / "underwriting_policy_summary.json", policy_summary)

    # Return summary
    return {
        "total_applicants": n_total,
        "approval_rate": approval_rate,
        "review_rate": review_rate,
        "decline_rate": decline_rate,
        "default_rate_by_decision": default_rate_by_decision,
        "total_expected_loss": float(decisions_df["expected_loss"].sum()),
        "champion_calibration": champion_calibration,
    }
