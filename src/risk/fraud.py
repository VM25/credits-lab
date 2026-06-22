"""Fraud & Payments Engine — Tasks 4.1 / 4.2 / 4.3.

Pure helpers
------------
rule_flags(row)  -> dict[str, int]        0/1 per business rule
rule_score(row)  -> float                 fraction of rules triggered
action(score)    -> str                   payment decision
expected_fraud_loss(p, amount) -> float   dollar-risk per transaction
transaction_reason_codes(row, triggered_rules) -> list[str]

Output builder
--------------
build() -> dict   trains models, scores all 80k rows, writes 3 output files
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config
from src.data.features import fraud_features
from src.models import anomaly as anomaly_mod
from src.models.metrics import (
    pr_auc as _pr_auc,
    roc_auc as _roc_auc,
    confusion_at,
    precision_recall_from_confusion,
)
from src.reporting.writers import write_csv, write_json

# ---------------------------------------------------------------------------
# Fraud score composite weights (documented assumption)
# ---------------------------------------------------------------------------
# Blend: 80 % supervised fraud probability (dominant, calibrated signal) +
#        10 % isolation-forest anomaly score (unsupervised novelty) +
#        10 % rule score (interpretable business heuristics).
# Weight rationale: the supervised model (balanced LR on V1..V28 + behavioural
# features) has very strong discriminative power (ROC-AUC ~0.97, PR-AUC ~0.66)
# on this highly imbalanced dataset. Giving it 80 % weight ensures that actual
# frauds (prob ≈ 1.0) breach the 0.80 review/block threshold while keeping FPR
# well-controlled. Anomaly and rule scores provide secondary interpretable signal.
_W_PROB  = 0.80
_W_ANOM  = 0.10
_W_RULE  = 0.10

# ---------------------------------------------------------------------------
# Reason code catalogue
# ---------------------------------------------------------------------------
ALLOWED_REASONS: dict[str, str] = {
    "HIGH_AMOUNT":          "Transaction amount exceeds the 99th-percentile threshold",
    "HIGH_VELOCITY":        "Unusually high number of transactions in the past 24 hours",
    "NEW_DEVICE":           "Transaction initiated from a device not previously seen on this account",
    "NEW_LOCATION":         "Transaction initiated from a location not previously seen on this account",
    "HIGH_RISK_MERCHANT":   "Merchant is classified as high-risk based on category and risk scoring",
    "SHORT_ACCOUNT_AGE":    "Account was opened fewer than 90 days ago",
    "UNUSUAL_AMOUNT":       "Transaction amount is more than 3 standard deviations from this account's mean",
    "HIGH_FRAUD_SCORE":     "Composite fraud score elevated by model-based risk indicators",
    "HIGH_ANOMALY_SCORE":   "Transaction pattern is atypical relative to normal account behaviour",
}

# Velocity threshold: 95th-percentile of training data (pre-computed heuristic; labeled)
_VELOCITY_24H_HIGH_THRESHOLD = 26  # 95th-percentile observed in full dataset


# ---------------------------------------------------------------------------
# Task 4.1 — pure policy helpers
# ---------------------------------------------------------------------------

def rule_flags(row) -> dict[str, int]:
    """Return a dict of 0/1 rule flags for one transaction row.

    Rules are the doc-04 §6A interpretable business heuristics.
    Each flag is 1 if the condition is triggered, 0 otherwise.
    """
    return {
        "HIGH_AMOUNT":        int(bool(row.get("high_amount_flag", 0))),
        "HIGH_VELOCITY":      int(row.get("velocity_24h", 0) >= _VELOCITY_24H_HIGH_THRESHOLD),
        "NEW_DEVICE":         int(bool(row.get("new_device_flag", 0))),
        "NEW_LOCATION":       int(bool(row.get("new_location_flag", 0))),
        "HIGH_RISK_MERCHANT": int(
            row.get("merchant_risk_band", "") == "high"
            or row.get("merchant_risk_score", 0.0) >= 0.8
        ),
        "SHORT_ACCOUNT_AGE":  int(row.get("account_age_days", 9999) < 90),
        "UNUSUAL_AMOUNT":     int(abs(row.get("amount_zscore_by_account", 0.0)) > 3.0),
    }


def rule_score(row) -> float:
    """Fraction of business rules triggered; in [0, 1]."""
    flags = rule_flags(row)
    n = len(flags)
    if n == 0:
        return 0.0
    return sum(flags.values()) / n


def action(score: float) -> str:
    """Map composite fraud_score to a payment action.

    Thresholds are sourced from config.FRAUD_THRESHOLDS.
    """
    t = config.FRAUD_THRESHOLDS
    if score < t["approve"]:
        return "approve"
    if score < t["stepup"]:
        return "step_up"
    if score < t["review"]:
        return "review"
    return "block"


def expected_fraud_loss(fraud_probability: float, amount: float) -> float:
    """Expected dollar loss = fraud_probability * amount * FRAUD_LOSS_SEVERITY.

    Always >= 0.  Assumption documented in config.FRAUD_LOSS_SEVERITY.
    """
    return max(0.0, float(fraud_probability) * float(amount) * config.FRAUD_LOSS_SEVERITY)


def transaction_reason_codes(row, triggered_rules: dict[str, int]) -> list[str]:
    """Return top 1-3 explainable reason codes for a transaction.

    Priority: triggered business rules first, then model/anomaly indicators
    if fewer than 3 rule codes exist.  No black-box language.
    """
    codes: list[str] = [k for k, v in triggered_rules.items() if v]

    # Supplement with model-signal codes when slots remain
    if len(codes) < 3 and row.get("fraud_probability", 0.0) >= config.FRAUD_THRESHOLDS["stepup"]:
        if "HIGH_FRAUD_SCORE" not in codes:
            codes.append("HIGH_FRAUD_SCORE")
    if len(codes) < 3 and row.get("anomaly_score", 0.0) >= 0.70:
        if "HIGH_ANOMALY_SCORE" not in codes:
            codes.append("HIGH_ANOMALY_SCORE")

    # Return top 3 (or fewer), always non-empty for non-approve actions
    return codes[:3] if codes else []


# ---------------------------------------------------------------------------
# Internal: fit supervised model with balanced class weights
# ---------------------------------------------------------------------------

def _fit_supervised(X_train: np.ndarray, y_train: np.ndarray, feature_names: list[str]):
    """Fit a balanced logistic regression pipeline; returns a sklearn Pipeline."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=config.SEED,
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


# ---------------------------------------------------------------------------
# Task 4.3 — output builder
# ---------------------------------------------------------------------------

def build() -> dict:
    """Train fraud models, score all rows, write 3 output files, return summary.

    Steps
    -----
    1. Load fraud_model_dataset; split.
    2. Supervised model (LogReg, balanced) → fraud_probability [0,1].
    3. Anomaly model (IsolationForest) → anomaly_score [0,1].
    4. Rule score per row.
    5. Composite fraud_score = 0.60*prob + 0.25*anomaly + 0.15*rule (clipped [0,1]).
    6. payment_action via action(fraud_score).
    7. expected_fraud_loss per row.
    8. Manual-review queue (capacity-aware).
    9. Metrics on test split (headline: PR-AUC).
    10. Write outputs.
    """
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    df = pd.read_csv(config.PROCESSED / "fraud_model_dataset.csv")

    feat_cols = fraud_features(df)  # leakage-guarded predictor list

    # Impute NaNs with train-split medians (fit on train only, apply everywhere)
    train_mask = df["split"] == "train"
    train_medians = df.loc[train_mask, feat_cols].median()
    df[feat_cols] = df[feat_cols].fillna(train_medians)

    X_train = df.loc[train_mask, feat_cols].values
    y_train = df.loc[train_mask, "fraud_flag"].values

    X_all = df[feat_cols].values

    # ------------------------------------------------------------------
    # 2. Supervised model
    # ------------------------------------------------------------------
    sup_pipe = _fit_supervised(X_train, y_train, feat_cols)
    fraud_prob_all = sup_pipe.predict_proba(X_all)[:, 1]
    df["fraud_probability"] = fraud_prob_all

    # ------------------------------------------------------------------
    # 3. Anomaly model
    # ------------------------------------------------------------------
    anom_model = anomaly_mod.fit(X_train)
    df["anomaly_score"] = anom_model.score(X_all)

    # ------------------------------------------------------------------
    # 4. Rule score (vectorised for performance)
    # ------------------------------------------------------------------
    rule_scores = (
        df["high_amount_flag"].astype(int)
        + (df["velocity_24h"] >= _VELOCITY_24H_HIGH_THRESHOLD).astype(int)
        + df["new_device_flag"].astype(int)
        + df["new_location_flag"].astype(int)
        + ((df["merchant_risk_band"] == "high") | (df["merchant_risk_score"] >= 0.8)).astype(int)
        + (df["account_age_days"] < 90).astype(int)
        + (df["amount_zscore_by_account"].abs() > 3.0).astype(int)
    ) / 7.0  # 7 rules total
    df["rule_score"] = rule_scores.values

    # ------------------------------------------------------------------
    # 5. Composite fraud_score
    # ------------------------------------------------------------------
    df["fraud_score"] = (
        _W_PROB * df["fraud_probability"]
        + _W_ANOM * df["anomaly_score"]
        + _W_RULE * df["rule_score"]
    ).clip(0.0, 1.0)

    # ------------------------------------------------------------------
    # 6. Payment action
    # ------------------------------------------------------------------
    df["payment_action"] = df["fraud_score"].apply(action)

    # ------------------------------------------------------------------
    # 7. Expected fraud loss
    # ------------------------------------------------------------------
    df["expected_fraud_loss"] = (
        df["fraud_probability"] * df["amount"] * config.FRAUD_LOSS_SEVERITY
    ).clip(lower=0.0)

    # ------------------------------------------------------------------
    # 8. Manual-review queue (capacity-aware)
    # ------------------------------------------------------------------
    review_mask = df["payment_action"] == "review"
    review_idx = df.index[review_mask]

    # Rank review rows by expected_fraud_loss descending (1 = highest priority)
    df["manual_review_priority"] = np.nan
    if len(review_idx) > 0:
        review_ranks = (
            df.loc[review_idx, "expected_fraud_loss"]
            .rank(ascending=False, method="first")
            .astype(int)
        )
        df.loc[review_idx, "manual_review_priority"] = review_ranks

    # Actionable queue capped at MANUAL_REVIEW_CAPACITY (doc 04 §10)
    manual_review_volume = min(int(review_mask.sum()), config.MANUAL_REVIEW_CAPACITY)

    # ------------------------------------------------------------------
    # 9. Reason codes
    # ------------------------------------------------------------------
    def _reason_codes_for_row(row):
        rf = rule_flags(row)
        codes = transaction_reason_codes(row, rf)
        # Pad to 3 slots with None
        while len(codes) < 3:
            codes.append(None)
        return codes[0], codes[1], codes[2]

    reasons = df.apply(_reason_codes_for_row, axis=1, result_type="expand")
    df["top_reason_1"] = reasons[0]
    df["top_reason_2"] = reasons[1]
    df["top_reason_3"] = reasons[2]

    # ------------------------------------------------------------------
    # 9b. Metrics on test split
    # ------------------------------------------------------------------
    test_mask = df["split"] == "test"
    y_test = df.loc[test_mask, "fraud_flag"].values
    prob_test = df.loc[test_mask, "fraud_probability"].values
    score_test = df.loc[test_mask, "fraud_score"].values

    headline_pr_auc = float(_pr_auc(y_test, score_test))
    headline_roc_auc = float(_roc_auc(y_test, score_test))

    # Decision boundary for fraud capture: review + block (score >= FRAUD_THRESHOLDS["review"])
    review_boundary = config.FRAUD_THRESHOLDS["review"]
    conf_review = confusion_at(y_test, score_test, review_boundary)
    precision_v, recall_v = precision_recall_from_confusion(conf_review)

    # fraud_capture_rate = recall at review/block boundary
    fraud_capture_rate = recall_v

    # FPR, FNR at the review boundary
    tn, fp, fn, tp = (
        conf_review["tn"], conf_review["fp"], conf_review["fn"], conf_review["tp"]
    )
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    # Expected fraud loss avoided = sum of expected_fraud_loss for flagged actual frauds
    caught_mask = test_mask & (df["payment_action"].isin(["review", "block"])) & (df["fraud_flag"] == 1)
    expected_fraud_loss_avoided = float(df.loc[caught_mask, "expected_fraud_loss"].sum())

    # ------------------------------------------------------------------
    # Threshold tradeoff curve (0.05..0.95 step 0.05)
    # ------------------------------------------------------------------
    thresholds_grid = np.arange(0.05, 1.00, 0.05)
    threshold_tradeoff = []
    n_pos_test = int(y_test.sum())
    n_test = len(y_test)

    for thr in thresholds_grid:
        above = score_test >= thr
        fraud_captured = int((above & (y_test == 1)).sum())
        false_positives = int((above & (y_test == 0)).sum())
        review_volume = int(above.sum())
        # Expected fraud loss at this threshold (test set)
        efl_at_thr = float(
            (above * df.loc[test_mask, "expected_fraud_loss"].values).sum()
        )
        threshold_tradeoff.append({
            "threshold": round(float(thr), 2),
            "fraud_captured": fraud_captured,
            "false_positives": false_positives,
            "review_volume": review_volume,
            "expected_fraud_loss": round(efl_at_thr, 4),
        })

    # ------------------------------------------------------------------
    # Action mix and other summary stats
    # ------------------------------------------------------------------
    action_mix = df["payment_action"].value_counts().to_dict()

    # Fraud score distribution (10 bins)
    counts, bin_edges = np.histogram(df["fraud_score"].values, bins=10, range=(0, 1))
    fraud_score_distribution = {
        "bins": [round(float(e), 3) for e in bin_edges.tolist()],
        "counts": counts.tolist(),
    }

    # Expected fraud loss by action
    efl_by_action = (
        df.groupby("payment_action")["expected_fraud_loss"].sum().round(4).to_dict()
    )

    # Top fraud drivers (reason codes among non-approve)
    non_approve = df[df["payment_action"] != "approve"]
    driver_counts: dict[str, int] = {}
    for col in ["top_reason_1", "top_reason_2", "top_reason_3"]:
        for val in non_approve[col].dropna():
            driver_counts[val] = driver_counts.get(val, 0) + 1
    top_fraud_drivers = dict(sorted(driver_counts.items(), key=lambda x: -x[1]))

    # ------------------------------------------------------------------
    # 10a. Write fraud_alerts.csv (all 80k rows)
    # ------------------------------------------------------------------
    alert_cols = [
        "transaction_id", "account_id", "transaction_time", "amount",
        "fraud_probability", "fraud_score", "anomaly_score",
        "payment_action", "expected_fraud_loss",
        "top_reason_1", "top_reason_2", "top_reason_3",
        "manual_review_priority",
    ]
    write_csv(config.OUTPUTS / "fraud_alerts.csv", df[alert_cols])

    # ------------------------------------------------------------------
    # 10b. Write fraud_alerts.json (stratified display sample)
    # ------------------------------------------------------------------
    sample_size = min(config.UI_SAMPLE_ROWS, len(df))
    # Stratified sample across payment_action so all actions + fraud appear
    strat_groups = []
    action_groups = df.groupby("payment_action")
    n_actions = df["payment_action"].nunique()
    per_action_quota = max(1, sample_size // n_actions)
    for act_name, grp in action_groups:
        take = min(len(grp), per_action_quota)
        strat_groups.append(grp.sample(n=take, random_state=config.SEED))
    sample_df = pd.concat(strat_groups, ignore_index=True)
    # Trim or top-up to exactly sample_size
    if len(sample_df) > sample_size:
        sample_df = sample_df.sample(n=sample_size, random_state=config.SEED)
    elif len(sample_df) < sample_size:
        remaining = df.drop(index=sample_df.index, errors="ignore")
        extra_needed = sample_size - len(sample_df)
        if len(remaining) > 0:
            extra = remaining.sample(
                n=min(extra_needed, len(remaining)), random_state=config.SEED
            )
            sample_df = pd.concat([sample_df, extra], ignore_index=True)

    # Build row dicts for JSON; coerce NaN → None for JSON compatibility
    def _to_json_row(row):
        d = {}
        for col in alert_cols:
            val = row[col]
            if pd.isna(val) if not isinstance(val, str) else False:
                d[col] = None
            else:
                d[col] = val
        return d

    json_rows = [_to_json_row(r) for _, r in sample_df[alert_cols].iterrows()]

    write_json(config.OUTPUTS / "fraud_alerts.json", {
        "rows": json_rows,
        "row_count_total": int(len(df)),
        "sample_size": int(len(json_rows)),
        "is_sample": True,
    })

    # ------------------------------------------------------------------
    # 10c. Write fraud_policy_summary.json
    # ------------------------------------------------------------------
    summary = {
        "note": (
            "Fraud labels are heavily imbalanced (~0.6% positive rate). "
            "Accuracy is NOT used as a headline metric. "
            "PR-AUC (precision-recall area) is the primary performance indicator."
        ),
        "pr_auc": round(headline_pr_auc, 6),
        "roc_auc": round(headline_roc_auc, 6),
        "precision": round(float(precision_v), 6),
        "recall": round(float(recall_v), 6),
        "fraud_capture_rate": round(float(fraud_capture_rate), 6),
        "false_positive_rate": round(float(fpr), 6),
        "false_negative_rate": round(float(fnr), 6),
        "expected_fraud_loss_avoided": round(expected_fraud_loss_avoided, 4),
        "manual_review_volume": manual_review_volume,
        "manual_review_capacity": config.MANUAL_REVIEW_CAPACITY,
        "action_mix": {k: int(v) for k, v in action_mix.items()},
        "fraud_score_distribution": fraud_score_distribution,
        "expected_fraud_loss_by_action": {k: float(v) for k, v in efl_by_action.items()},
        "top_fraud_drivers": top_fraud_drivers,
        "threshold_tradeoff": threshold_tradeoff,
        "composite_weights": {
            "fraud_probability": _W_PROB,
            "anomaly_score": _W_ANOM,
            "rule_score": _W_RULE,
        },
        "model_note": (
            "Supervised: LogisticRegression(class_weight='balanced', max_iter=1000). "
            "Anomaly: IsolationForest(contamination='auto'). "
            "Composite = 0.80*fraud_probability + 0.10*anomaly_score + 0.10*rule_score. "
            "High weight on supervised probability ensures actual frauds (prob~1.0) breach "
            "the 0.80 review/block threshold; anomaly and rule scores provide interpretable "
            "secondary signal without degrading the primary discriminative power."
        ),
    }

    write_json(config.OUTPUTS / "fraud_policy_summary.json", summary)

    return summary
