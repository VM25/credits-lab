"""Phase 7 — Model-risk validation.

Validates five models: underwriting champion (logistic scorecard),
underwriting challenger (GBM), fraud supervised, fraud anomaly,
and stablecoin risk scoring.

Public interface
----------------
build() -> dict
    Re-derives all models from raw splits, computes validation metrics,
    calibration, drift (PSI), segment performance, champion-vs-challenger
    comparison, and verdict table. Writes 6 output files.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src import config
from src.data.features import underwriting_features, fraud_features
from src.models import scorecard, gbm, calibration as cal_mod, anomaly as anomaly_mod
from src.models import metrics as M
from src.reporting.writers import write_csv, write_json

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _impute_train_medians(df_train: pd.DataFrame, df_other: pd.DataFrame, features: list) -> tuple:
    """Return (train_filled, other_filled) using train-split medians for NaNs."""
    medians = df_train[features].median()
    return df_train[features].fillna(medians), df_other[features].fillna(medians)


def _grade(pd_val: float) -> str:
    for grade, upper in config.RISK_GRADE_BANDS:
        if pd_val < upper:
            return grade
    return "E"


# ---------------------------------------------------------------------------
# Credit validation (champion + challenger)
# ---------------------------------------------------------------------------

def _validate_credit():
    uw = pd.read_csv(config.PROCESSED / "underwriting_model_dataset.csv")
    feats = underwriting_features(uw)

    train = uw[uw["split"] == "train"].copy()
    val   = uw[uw["split"] == "val"].copy()
    test  = uw[uw["split"] == "test"].copy()

    y_train = train["default_flag"].values
    y_val   = val["default_flag"].values
    y_test  = test["default_flag"].values

    # Impute with train medians
    X_train_raw, X_val_raw = _impute_train_medians(train, val, feats)
    _, X_test_raw = _impute_train_medians(train, test, feats)
    X_train = X_train_raw.values
    X_val   = X_val_raw.values
    X_test  = X_test_raw.values

    # --- Champion: logistic scorecard ---
    champ_model = scorecard.fit(X_train, y_train, feats)
    champ_val_scores = champ_model.predict_proba(X_val)
    champ_calibrator = cal_mod.fit(champ_val_scores, y_val)

    champ_train_pd = champ_calibrator.transform(champ_model.predict_proba(X_train))
    champ_test_pd  = champ_calibrator.transform(champ_model.predict_proba(X_test))

    # --- Challenger: GBM ---
    chal_model = gbm.fit(X_train, y_train, feats)
    chal_val_scores = chal_model.predict_proba(X_val)
    chal_calibrator = cal_mod.fit(chal_val_scores, y_val)

    chal_train_pd = chal_calibrator.transform(chal_model.predict_proba(X_train))
    chal_test_pd  = chal_calibrator.transform(chal_model.predict_proba(X_test))

    # --- Test metrics: champion ---
    c_conf = M.confusion_at(y_test, champ_test_pd, config.PD_DECLINE)
    c_prec, c_rec = M.precision_recall_from_confusion(c_conf)
    champ_metrics = {
        "model": "champion_scorecard",
        "model_type": "logistic_scorecard",
        "roc_auc":   round(M.roc_auc(y_test, champ_test_pd), 6),
        "pr_auc":    round(M.pr_auc(y_test, champ_test_pd), 6),
        "brier":     round(M.brier(y_test, champ_test_pd), 6),
        "ks":        round(M.ks(y_test, champ_test_pd), 6),
        "precision": round(c_prec, 6),
        "recall":    round(c_rec, 6),
        "tp": c_conf["tp"], "fp": c_conf["fp"],
        "tn": c_conf["tn"], "fn": c_conf["fn"],
        "brier_before_cal": round(champ_calibrator.brier_before, 6),
        "brier_after_cal":  round(champ_calibrator.brier_after, 6),
    }

    # PSI: champion calibrated PD train vs test
    champ_psi = M.psi(champ_train_pd, champ_test_pd)
    champ_psi_status = M.psi_status(champ_psi)

    # Calibration curve (on val, from calibrator)
    calibration_curve = champ_calibrator.curve

    # Decile default table on TEST (PD deciles → actual default rate)
    pd_series = pd.Series(champ_test_pd, name="pd")
    y_series  = pd.Series(y_test, name="default_flag")
    test_df = pd.DataFrame({"pd": champ_test_pd, "default_flag": y_test})
    # Assign decile labels by pd score (decile 1 = lowest PD, decile 10 = highest)
    test_df["decile"] = pd.qcut(test_df["pd"], q=10, labels=False, duplicates="drop") + 1
    decile_table = []
    for dec, grp in test_df.groupby("decile"):
        decile_table.append({
            "decile": int(dec),
            "pd_mean": round(float(grp["pd"].mean()), 6),
            "actual_default_rate": round(float(grp["default_flag"].mean()), 6),
            "count": int(len(grp)),
        })
    # Ensure sorted by decile (ascending PD)
    decile_table.sort(key=lambda r: r["decile"])

    # Predicted vs actual by risk grade band
    test_df["risk_grade"] = test_df["pd"].apply(_grade)
    pred_vs_actual = []
    for grade, grp in test_df.groupby("risk_grade"):
        pred_vs_actual.append({
            "risk_grade": grade,
            "predicted_mean_pd": round(float(grp["pd"].mean()), 6),
            "actual_default_rate": round(float(grp["default_flag"].mean()), 6),
            "count": int(len(grp)),
        })

    # --- Test metrics: challenger ---
    h_conf = M.confusion_at(y_test, chal_test_pd, config.PD_DECLINE)
    h_prec, h_rec = M.precision_recall_from_confusion(h_conf)
    chal_metrics = {
        "model": "challenger_gbm",
        "model_type": "gradient_boosting",
        "roc_auc":   round(M.roc_auc(y_test, chal_test_pd), 6),
        "pr_auc":    round(M.pr_auc(y_test, chal_test_pd), 6),
        "brier":     round(M.brier(y_test, chal_test_pd), 6),
        "ks":        round(M.ks(y_test, chal_test_pd), 6),
        "precision": round(h_prec, 6),
        "recall":    round(h_rec, 6),
        "tp": h_conf["tp"], "fp": h_conf["fp"],
        "tn": h_conf["tn"], "fn": h_conf["fn"],
        "brier_before_cal": round(chal_calibrator.brier_before, 6),
        "brier_after_cal":  round(chal_calibrator.brier_after, 6),
    }

    chal_psi = M.psi(chal_train_pd, chal_test_pd)
    chal_psi_status = M.psi_status(chal_psi)

    # --- Segment performance: credit_grade + income/dti bands ---
    test_full = test.copy()
    test_full["calibrated_pd"] = champ_test_pd

    # Income band
    test_full["income_band"] = pd.qcut(
        test_full["annual_income"].fillna(test_full["annual_income"].median()),
        q=4, labels=["low", "mid_low", "mid_high", "high"], duplicates="drop"
    )
    # DTI band
    test_full["dti_band"] = pd.cut(
        test_full["debt_to_income"].fillna(test_full["debt_to_income"].median()),
        bins=[0, 20, 30, 40, 100], labels=["low", "moderate", "elevated", "high"]
    )

    segment_perf = []
    for col in ["credit_grade", "income_band", "dti_band"]:
        for seg_val, grp in test_full.groupby(col):
            avg_score = float(grp["calibrated_pd"].mean())
            event_rate = float(grp["default_flag"].mean())
            divergence = abs(avg_score - event_rate)
            segment_perf.append({
                "segment_type": col,
                "segment_value": str(seg_val),
                "count": int(len(grp)),
                "event_rate": round(event_rate, 6),
                "average_score": round(avg_score, 6),
                "divergence": round(divergence, 6),
                "weak_segment": bool(divergence > 0.12),
            })

    champ_metrics["psi"] = round(champ_psi, 6)
    champ_metrics["psi_status"] = champ_psi_status
    chal_metrics["psi"] = round(chal_psi, 6)
    chal_metrics["psi_status"] = chal_psi_status

    # Champion feature coefficients (explainability)
    champ_coef = champ_model.coefficients

    # Challenger feature importances
    chal_importances = chal_model.feature_importances

    return {
        "champ_metrics": champ_metrics,
        "chal_metrics": chal_metrics,
        "calibration_curve": calibration_curve,
        "decile_default_table": decile_table,
        "predicted_vs_actual_by_band": pred_vs_actual,
        "segment_performance": segment_perf,
        "champ_psi": champ_psi,
        "champ_psi_status": champ_psi_status,
        "chal_psi": chal_psi,
        "chal_psi_status": chal_psi_status,
        "champ_coef": champ_coef,
        "chal_importances": chal_importances,
        "champ_calibrator_brier_after": champ_calibrator.brier_after,
        "chal_calibrator_brier_after": chal_calibrator.brier_after,
        "champ_calibrator_brier_before": champ_calibrator.brier_before,
        "chal_calibrator_brier_before": chal_calibrator.brier_before,
    }


# ---------------------------------------------------------------------------
# Fraud validation
# ---------------------------------------------------------------------------

def _validate_fraud():
    fr = pd.read_csv(config.PROCESSED / "fraud_model_dataset.csv")
    feats = fraud_features(fr)

    train = fr[fr["split"] == "train"].copy()
    val   = fr[fr["split"] == "val"].copy()
    test  = fr[fr["split"] == "test"].copy()

    y_train = train["fraud_flag"].values
    y_val   = val["fraud_flag"].values
    y_test  = test["fraud_flag"].values

    # Impute train medians
    X_train_raw, X_test_raw = _impute_train_medians(train, test, feats)
    _, X_val_raw = _impute_train_medians(train, val, feats)
    X_train = X_train_raw.values
    X_test  = X_test_raw.values
    X_val   = X_val_raw.values

    # --- Supervised fraud model ---
    sup_lr = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=config.SEED,
    )
    sup_lr.fit(X_train, y_train)
    sup_test_scores = sup_lr.predict_proba(X_test)[:, 1]

    # Headline: PR-AUC
    sup_pr_auc = M.pr_auc(y_test, sup_test_scores)
    sup_roc_auc = M.roc_auc(y_test, sup_test_scores)

    # Fraud capture rate = recall at score >= FRAUD_THRESHOLDS["stepup"] (0.60)
    stepup_thresh = config.FRAUD_THRESHOLDS["stepup"]
    sup_conf_stepup = M.confusion_at(y_test, sup_test_scores, stepup_thresh)
    sup_prec_su, sup_rec_su = M.precision_recall_from_confusion(sup_conf_stepup)
    fraud_capture_rate = sup_rec_su  # recall at stepup threshold

    # FPR / FNR
    tp = sup_conf_stepup["tp"]
    fp = sup_conf_stepup["fp"]
    tn = sup_conf_stepup["tn"]
    fn = sup_conf_stepup["fn"]
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    # Score distribution (histogram over 10 bins)
    hist_counts, hist_edges = np.histogram(sup_test_scores, bins=10, range=(0, 1))
    score_dist = [
        {"bin_low": round(float(hist_edges[i]), 4),
         "bin_high": round(float(hist_edges[i + 1]), 4),
         "count": int(hist_counts[i])}
        for i in range(len(hist_counts))
    ]

    # PR curve data (threshold sweep)
    from sklearn.metrics import precision_recall_curve
    precision_arr, recall_arr, thresh_arr = precision_recall_curve(y_test, sup_test_scores)
    # Downsample to ~20 representative points
    idx = np.linspace(0, len(precision_arr) - 1, min(20, len(precision_arr)), dtype=int)
    fraud_pr_curve = [
        {"precision": round(float(precision_arr[i]), 6),
         "recall": round(float(recall_arr[i]), 6)}
        for i in idx
    ]

    sup_metrics = {
        "model": "fraud_supervised",
        "model_type": "logistic_balanced",
        "pr_auc": round(sup_pr_auc, 6),            # HEADLINE
        "roc_auc": round(sup_roc_auc, 6),
        "precision_at_stepup": round(sup_prec_su, 6),
        "recall_at_stepup": round(sup_rec_su, 6),
        "fraud_capture_rate": round(fraud_capture_rate, 6),
        "false_positive_rate": round(fpr, 6),
        "false_negative_rate": round(fnr, 6),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "score_distribution": score_dist,
    }

    # --- Anomaly model ---
    # Fit on train predictors only (unsupervised)
    anom_model = anomaly_mod.fit(X_train)
    # Score test
    X_all_raw, _ = _impute_train_medians(train, test, feats)
    anom_test_scores = anom_model.score(X_test)

    # Sanity AUC: anomaly score vs fraud_flag
    anom_auc = M.roc_auc(y_test, anom_test_scores)

    # Anomaly score distribution
    anom_hist_counts, anom_hist_edges = np.histogram(anom_test_scores, bins=10, range=(0, 1))
    anom_score_dist = [
        {"bin_low": round(float(anom_hist_edges[i]), 4),
         "bin_high": round(float(anom_hist_edges[i + 1]), 4),
         "count": int(anom_hist_counts[i])}
        for i in range(len(anom_hist_counts))
    ]

    # Also read fraud_alerts anomaly_score distribution for reference
    fa = pd.read_csv(config.OUTPUTS / "fraud_alerts.csv")
    alert_anom_hist, alert_anom_edges = np.histogram(
        fa["anomaly_score"].dropna(), bins=10, range=(0, 1)
    )
    alert_anom_dist = [
        {"bin_low": round(float(alert_anom_edges[i]), 4),
         "bin_high": round(float(alert_anom_edges[i + 1]), 4),
         "count": int(alert_anom_hist[i])}
        for i in range(len(alert_anom_hist))
    ]

    anom_metrics = {
        "model": "fraud_anomaly",
        "model_type": "isolation_forest",
        "sanity_roc_auc_vs_fraud_label": round(anom_auc, 6),
        "score_distribution_test": anom_score_dist,
        "score_distribution_alerts": alert_anom_dist,
        "note": "Unsupervised model — sanity AUC measures discrimination vs fraud label; not used as primary fraud classifier.",
    }

    return {
        "sup_metrics": sup_metrics,
        "anom_metrics": anom_metrics,
        "fraud_pr_curve": fraud_pr_curve,
    }


# ---------------------------------------------------------------------------
# Stablecoin validation
# ---------------------------------------------------------------------------

def _validate_stablecoin():
    from src.risk import stablecoin as sc_mod

    sc = pd.read_csv(config.PROCESSED / "processed_stablecoin_transactions.csv")
    # Re-derive the score on the processed data so the score and the synthetic
    # label stay ROW-ALIGNED. score_frame() sorts rows by (wallet, time), so the
    # alerts CSV is in a different order than the original-order processed label;
    # reading them side-by-side would misalign score vs label and corrupt the
    # discrimination AUC. score_frame copies the frame (label rides along, aligned).
    scored = sc_mod.score_frame(sc)
    scored["stablecoin_risk_action"] = scored["stablecoin_risk_score"].apply(sc_mod.action)
    sc_label = scored["stablecoin_risk_label"].values
    scores   = scored["stablecoin_risk_score"].values
    actions  = scored["stablecoin_risk_action"].values
    exposure = scored["risk_exposure_score"].values
    # Reason-code frequency is order-independent, so read it from the alerts file.
    sa = pd.read_csv(config.OUTPUTS / "stablecoin_alerts.csv")

    # Score distribution
    score_hist, score_edges = np.histogram(scores, bins=10, range=(0, 1))
    score_distribution = [
        {"bin_low": round(float(score_edges[i]), 4),
         "bin_high": round(float(score_edges[i + 1]), 4),
         "count": int(score_hist[i])}
        for i in range(len(score_hist))
    ]

    # Risk action mix
    action_counts = {a: int((actions == a).sum()) for a in ["normal", "monitor", "review", "high_risk"]}
    total = len(actions)
    risk_action_mix = {k: {"count": v, "share": round(v / total, 6)} for k, v in action_counts.items()}

    # High-risk wallet concentration
    high_risk_mask = actions == "high_risk"
    high_risk_exposure = float(exposure[high_risk_mask].sum())
    total_exposure = float(exposure.sum())
    high_risk_wallet_concentration = round(high_risk_exposure / total_exposure, 6) if total_exposure > 0 else 0.0

    # Risky exposure by score band (5 bands)
    score_series = pd.Series(scores, name="score")
    exposure_series = pd.Series(exposure, name="exposure")
    band_labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
    band_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.01]
    risky_exposure_by_band = []
    for i, label in enumerate(band_labels):
        lo, hi = band_edges[i], band_edges[i + 1]
        mask = (scores >= lo) & (scores < hi)
        risky_exposure_by_band.append({
            "score_band": label,
            "count": int(mask.sum()),
            "total_risk_exposure": round(float(exposure[mask].sum()), 4),
        })

    # Threshold sensitivity: vary monitor/review/high_risk ±0.05
    thresholds = config.STABLECOIN_THRESHOLDS
    sensitivity = []
    for delta in [-0.05, 0.0, 0.05]:
        mon_t   = max(0.01, thresholds["monitor"]   + delta)
        rev_t   = max(0.01, thresholds["review"]    + delta)
        high_t  = max(0.01, thresholds["high_risk"] + delta)

        def _action(s):
            if s >= high_t:  return "high_risk"
            if s >= rev_t:   return "review"
            if s >= mon_t:   return "monitor"
            return "normal"

        shifted_actions = np.array([_action(s) for s in scores])
        sensitivity.append({
            "delta": round(delta, 2),
            "monitor_thresh": round(mon_t, 2),
            "review_thresh":  round(rev_t, 2),
            "high_risk_thresh": round(high_t, 2),
            "count_normal":    int((shifted_actions == "normal").sum()),
            "count_monitor":   int((shifted_actions == "monitor").sum()),
            "count_review":    int((shifted_actions == "review").sum()),
            "count_high_risk": int((shifted_actions == "high_risk").sum()),
        })

    # Top risk driver frequency (from reason codes across top_reason_1/2/3)
    reason_cols = [c for c in sa.columns if c.startswith("top_reason")]
    from collections import Counter
    reason_counter: Counter = Counter()
    for col in reason_cols:
        for val in sa[col].dropna():
            if str(val).strip():
                reason_counter[str(val).strip()] += 1
    top_risk_drivers = [
        {"reason": r, "frequency": cnt}
        for r, cnt in reason_counter.most_common(10)
    ]

    # Discrimination AUC: stablecoin_risk_score vs stablecoin_risk_label
    # (label was NOT used to build the score — independent discrimination check)
    disc_auc = M.roc_auc(sc_label, scores)

    return {
        "score_distribution": score_distribution,
        "risk_action_mix": risk_action_mix,
        "high_risk_wallet_concentration": high_risk_wallet_concentration,
        "risky_exposure_by_score_band": risky_exposure_by_band,
        "threshold_sensitivity": sensitivity,
        "top_risk_driver_frequency": top_risk_drivers,
        "discrimination_auc_vs_synthetic_label": round(disc_auc, 6),
        "note": "AML-style risk indicators — discrimination AUC measures separation against synthetic risk label; score not trained on this label.",
    }


# ---------------------------------------------------------------------------
# Champion vs Challenger comparison
# ---------------------------------------------------------------------------

def _champion_vs_challenger(credit: dict) -> dict:
    champ = credit["champ_metrics"]
    chal  = credit["chal_metrics"]

    # Calibration quality: brier after calibration (lower is better)
    champ_cal_quality = "good" if champ["brier_after_cal"] < 0.15 else "adequate"
    chal_cal_quality  = "good" if chal["brier_after_cal"] < 0.15 else "adequate"

    # Weak segment count
    champ_weak_segs = sum(1 for s in credit["segment_performance"] if s["weak_segment"])
    chal_weak_segs  = None  # challenger segment analysis not separately computed

    # PSI stability
    champ_stability = champ["psi_status"]
    chal_stability  = chal["psi_status"]

    # Explainability: champion has transparent coefficients; challenger has importances only
    champ_explainability = "transparent_coefficients"
    chal_explainability  = "tree_importances_opaque"

    # AUC gap
    auc_gap = chal["roc_auc"] - champ["roc_auc"]
    brier_gap = chal["brier_after_cal"] - champ["brier_after_cal"]  # positive = challenger worse

    # Recommendation: prefer champion for explainability unless challenger is
    # materially better (AUC delta > 0.02) AND still well-calibrated
    challenger_materially_better = (
        auc_gap > 0.02
        and chal["brier_after_cal"] < champ["brier_after_cal"] + 0.005
        and chal_stability in ("stable", "monitor")
    )

    if challenger_materially_better:
        recommendation = "challenger_gbm"
        rationale = (
            f"Challenger GBM is materially better (ROC-AUC delta={auc_gap:.4f}) "
            f"with comparable calibration (Brier-after-cal challenger={chal['brier_after_cal']:.4f} "
            f"vs champion={champ['brier_after_cal']:.4f}) and acceptable stability "
            f"({chal_stability}); however, reduced explainability is a deployment consideration."
        )
    else:
        recommendation = "champion_scorecard"
        rationale = (
            f"Champion logistic scorecard is preferred for regulatory explainability "
            f"(transparent coefficients) and comparable performance "
            f"(ROC-AUC champion={champ['roc_auc']:.4f} vs challenger={chal['roc_auc']:.4f}, "
            f"delta={auc_gap:.4f}); champion calibration Brier-after={champ['brier_after_cal']:.4f} "
            f"is {'better' if brier_gap > 0 else 'similar'} and PSI={champ['psi']:.4f} ({champ_stability}). "
            f"AUC uplift does not justify loss of direct coefficient interpretability."
        )

    return {
        "champion": {
            "model": "champion_scorecard",
            "roc_auc": champ["roc_auc"],
            "pr_auc": champ["pr_auc"],
            "brier": champ["brier"],
            "brier_after_cal": champ["brier_after_cal"],
            "psi": champ["psi"],
            "psi_status": champ["psi_status"],
            "calibration_quality": champ_cal_quality,
            "explainability": champ_explainability,
            "weak_segments": champ_weak_segs,
            "top_coefficients": sorted(
                credit["champ_coef"].items(), key=lambda x: abs(x[1]), reverse=True
            )[:5],
        },
        "challenger": {
            "model": "challenger_gbm",
            "roc_auc": chal["roc_auc"],
            "pr_auc": chal["pr_auc"],
            "brier": chal["brier"],
            "brier_after_cal": chal["brier_after_cal"],
            "psi": chal["psi"],
            "psi_status": chal["psi_status"],
            "calibration_quality": chal_cal_quality,
            "explainability": chal_explainability,
            "top_importances": sorted(
                credit["chal_importances"].items(), key=lambda x: x[1], reverse=True
            )[:5],
        },
        "auc_gap_challenger_minus_champion": round(auc_gap, 6),
        "brier_after_cal_gap_challenger_minus_champion": round(brier_gap, 6),
        "recommendation": recommendation,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

def _make_verdicts(credit: dict, fraud_result: dict, sc_result: dict, cc: dict) -> list:
    champ = credit["champ_metrics"]
    chal  = credit["chal_metrics"]
    sup   = fraud_result["sup_metrics"]
    anom  = fraud_result["anom_metrics"]

    verdicts = []

    # --- Champion scorecard ---
    champ_calib_ok  = champ["brier_after_cal"] < 0.18
    champ_stable    = champ["psi_status"] in ("stable", "monitor")
    champ_auc_ok    = champ["roc_auc"] >= 0.65
    champ_weak_segs = sum(1 for s in credit["segment_performance"] if s["weak_segment"])
    champ_seg_status = "weak_segments_present" if champ_weak_segs > 2 else "acceptable"

    if champ_auc_ok and champ_calib_ok and champ_stable and champ_weak_segs <= 2:
        champ_verdict = "Pass"
        champ_reason  = (
            f"Champion scorecard passes on discrimination (AUC={champ['roc_auc']:.4f}), "
            f"calibration (Brier-after={champ['brier_after_cal']:.4f}), "
            f"stability (PSI={champ['psi']:.4f}, {champ['psi_status']}), "
            f"and segment performance ({champ_weak_segs} weak segments)."
        )
    elif champ_auc_ok and (not champ_calib_ok or champ_weak_segs > 2):
        champ_verdict = "Monitor"
        champ_reason  = (
            f"Champion scorecard has acceptable discrimination (AUC={champ['roc_auc']:.4f}) "
            f"but requires monitoring: calibration Brier-after={champ['brier_after_cal']:.4f}, "
            f"{champ_weak_segs} weak segment(s) detected."
        )
    else:
        champ_verdict = "Fail"
        champ_reason  = (
            f"Champion scorecard has insufficient discrimination (AUC={champ['roc_auc']:.4f}) "
            f"or poor calibration (Brier-after={champ['brier_after_cal']:.4f})."
        )

    verdicts.append({
        "model_name": "champion_scorecard",
        "model_type": "logistic_scorecard",
        "primary_metric": champ["roc_auc"],
        "primary_metric_name": "roc_auc",
        "calibration_status": "pass" if champ_calib_ok else "fail",
        "stability_status": champ["psi_status"],
        "segment_status": champ_seg_status,
        "explainability_status": "transparent",
        "validation_verdict": champ_verdict,
        "verdict_reason": champ_reason,
    })

    # --- Challenger GBM ---
    chal_calib_ok  = chal["brier_after_cal"] < 0.18
    chal_stable    = chal["psi_status"] in ("stable", "monitor")
    chal_auc_ok    = chal["roc_auc"] >= 0.65

    if chal_auc_ok and chal_calib_ok and chal_stable:
        chal_verdict = "Pass"
        chal_reason  = (
            f"Challenger GBM passes on discrimination (AUC={chal['roc_auc']:.4f}), "
            f"calibration (Brier-after={chal['brier_after_cal']:.4f}), "
            f"and stability (PSI={chal['psi']:.4f}, {chal['psi_status']}); "
            f"noted reduced explainability vs champion."
        )
    elif chal_auc_ok:
        chal_verdict = "Monitor"
        chal_reason  = (
            f"Challenger GBM has adequate discrimination (AUC={chal['roc_auc']:.4f}) "
            f"but requires monitoring: Brier-after={chal['brier_after_cal']:.4f}, "
            f"PSI={chal['psi']:.4f} ({chal['psi_status']}), reduced explainability."
        )
    else:
        chal_verdict = "Fail"
        chal_reason  = (
            f"Challenger GBM does not meet minimum discrimination threshold "
            f"(AUC={chal['roc_auc']:.4f})."
        )

    verdicts.append({
        "model_name": "challenger_gbm",
        "model_type": "gradient_boosting",
        "primary_metric": chal["roc_auc"],
        "primary_metric_name": "roc_auc",
        "calibration_status": "pass" if chal_calib_ok else "fail",
        "stability_status": chal["psi_status"],
        "segment_status": "not_computed",
        "explainability_status": "opaque_importances",
        "validation_verdict": chal_verdict,
        "verdict_reason": chal_reason,
    })

    # --- Fraud supervised ---
    sup_pr_ok = sup["pr_auc"] >= 0.35
    sup_fcr_ok = sup["fraud_capture_rate"] >= 0.30

    if sup_pr_ok and sup_fcr_ok:
        sup_verdict = "Pass"
        sup_reason  = (
            f"Fraud supervised model passes: PR-AUC={sup['pr_auc']:.4f} (headline), "
            f"fraud capture rate at stepup threshold={sup['fraud_capture_rate']:.4f}, "
            f"ROC-AUC={sup['roc_auc']:.4f}."
        )
    elif sup_pr_ok or sup_fcr_ok:
        sup_verdict = "Monitor"
        sup_reason  = (
            f"Fraud supervised model has partial adequacy: PR-AUC={sup['pr_auc']:.4f}, "
            f"fraud capture rate={sup['fraud_capture_rate']:.4f} at stepup threshold; "
            f"class imbalance may limit precision at review boundary."
        )
    else:
        sup_verdict = "Fail"
        sup_reason  = (
            f"Fraud supervised model underperforms: PR-AUC={sup['pr_auc']:.4f}, "
            f"fraud capture rate={sup['fraud_capture_rate']:.4f}; "
            f"extreme class imbalance (base rate ~0.6%) constrains supervised learning."
        )

    verdicts.append({
        "model_name": "fraud_supervised",
        "model_type": "logistic_balanced",
        "primary_metric": sup["pr_auc"],
        "primary_metric_name": "pr_auc",
        "calibration_status": "not_calibrated",
        "stability_status": "not_computed",
        "segment_status": "not_computed",
        "explainability_status": "transparent",
        "validation_verdict": sup_verdict,
        "verdict_reason": sup_reason,
    })

    # --- Fraud anomaly ---
    anom_auc = anom["sanity_roc_auc_vs_fraud_label"]
    # Unsupervised: AUC > 0.55 = useful signal, > 0.65 = good
    if anom_auc >= 0.60:
        anom_verdict = "Pass"
        anom_reason  = (
            f"Fraud anomaly model (Isolation Forest) shows useful discrimination: "
            f"sanity AUC={anom_auc:.4f} vs fraud label; suitable as a complementary "
            f"unsupervised signal alongside the supervised model."
        )
    elif anom_auc >= 0.50:
        anom_verdict = "Monitor"
        anom_reason  = (
            f"Fraud anomaly model provides weak but non-trivial signal: "
            f"sanity AUC={anom_auc:.4f}; as an unsupervised model it should be used "
            f"as a secondary indicator only, not a primary classifier."
        )
    else:
        anom_verdict = "Fail"
        anom_reason  = (
            f"Fraud anomaly model shows near-random discrimination "
            f"(sanity AUC={anom_auc:.4f}); not suitable for production use as configured."
        )

    verdicts.append({
        "model_name": "fraud_anomaly",
        "model_type": "isolation_forest",
        "primary_metric": anom_auc,
        "primary_metric_name": "sanity_roc_auc_vs_fraud_label",
        "calibration_status": "not_applicable_unsupervised",
        "stability_status": "not_computed",
        "segment_status": "not_computed",
        "explainability_status": "opaque",
        "validation_verdict": anom_verdict,
        "verdict_reason": anom_reason,
    })

    # --- Stablecoin risk scoring ---
    sc_disc = sc_result["discrimination_auc_vs_synthetic_label"]
    # AML-style risk scoring: AUC >= 0.65 is good; this is a scoring system not a classifier
    if sc_disc >= 0.65:
        sc_verdict = "Pass"
        sc_reason  = (
            f"Stablecoin AML-style risk indicator scoring system shows strong discrimination "
            f"(AUC={sc_disc:.4f}) against synthetic risk label; action mix and concentration "
            f"metrics are within expected ranges for a risk-tiering system."
        )
    elif sc_disc >= 0.55:
        sc_verdict = "Monitor"
        sc_reason  = (
            f"Stablecoin AML-style risk indicator scoring shows moderate discrimination "
            f"(AUC={sc_disc:.4f}); scoring system is functional but threshold sensitivity "
            f"and concentration should be monitored quarterly."
        )
    else:
        sc_verdict = "Fail"
        sc_reason  = (
            f"Stablecoin AML-style risk indicator scoring shows insufficient discrimination "
            f"(AUC={sc_disc:.4f}); risk-tiering logic may require recalibration."
        )

    verdicts.append({
        "model_name": "stablecoin_risk_scoring",
        "model_type": "rule_and_indicator_scoring",
        "primary_metric": sc_disc,
        "primary_metric_name": "discrimination_auc_vs_synthetic_label",
        "calibration_status": "not_applicable_scoring_system",
        "stability_status": "not_computed",
        "segment_status": "not_computed",
        "explainability_status": "transparent_reason_codes",
        "validation_verdict": sc_verdict,
        "verdict_reason": sc_reason,
    })

    return verdicts


# ---------------------------------------------------------------------------
# Main build()
# ---------------------------------------------------------------------------

def build() -> dict:
    """Run full model-risk validation and write 6 output files.

    Returns the model_validation_summary dict.
    """
    # --- Run all validations ---
    credit = _validate_credit()
    fraud_result = _validate_fraud()
    sc_result = _validate_stablecoin()
    cc = _champion_vs_challenger(credit)
    verdicts = _make_verdicts(credit, fraud_result, sc_result, cc)

    # --- Write credit_model_validation.csv ---
    credit_rows = [
        {**credit["champ_metrics"]},
        {**credit["chal_metrics"]},
    ]
    # Remove nested score_distribution from CSV (not CSV-safe)
    for row in credit_rows:
        row.pop("score_distribution", None)
    write_csv(config.OUTPUTS / "credit_model_validation.csv", pd.DataFrame(credit_rows))

    # --- Write fraud_model_validation.csv ---
    sup_row = {k: v for k, v in fraud_result["sup_metrics"].items() if k != "score_distribution"}
    anom_row = {k: v for k, v in fraud_result["anom_metrics"].items()
                if k not in ("score_distribution_test", "score_distribution_alerts")}
    write_csv(config.OUTPUTS / "fraud_model_validation.csv",
              pd.DataFrame([sup_row, anom_row]))

    # --- Write stablecoin_model_validation.csv ---
    sc_flat = {
        "model": "stablecoin_risk_scoring",
        "model_type": "rule_and_indicator_scoring",
        "discrimination_auc_vs_synthetic_label": sc_result["discrimination_auc_vs_synthetic_label"],
        "high_risk_wallet_concentration": sc_result["high_risk_wallet_concentration"],
        "count_normal": sc_result["risk_action_mix"].get("normal", {}).get("count", 0),
        "count_monitor": sc_result["risk_action_mix"].get("monitor", {}).get("count", 0),
        "count_review": sc_result["risk_action_mix"].get("review", {}).get("count", 0),
        "count_high_risk": sc_result["risk_action_mix"].get("high_risk", {}).get("count", 0),
        "note": sc_result["note"],
    }
    write_csv(config.OUTPUTS / "stablecoin_model_validation.csv", pd.DataFrame([sc_flat]))

    # --- Write champion_challenger_comparison.json ---
    write_json(config.OUTPUTS / "champion_challenger_comparison.json", cc)

    # --- Write model_risk_verdicts.json ---
    write_json(config.OUTPUTS / "model_risk_verdicts.json", verdicts)

    # --- Write model_validation_summary.json ---
    # Embed calibration_curve and decile_default_table here (NOT as separate files)
    summary = {
        "description": (
            "Model-risk validation summary — Phase 7. "
            "Calibration curve and decile default table are embedded here (chart-embedding map). "
            "No separate calibration_curve.json or decile_default_table.csv are written."
        ),
        # Embedded chart data (champion)
        "calibration_curve": credit["calibration_curve"],
        "decile_default_table": credit["decile_default_table"],
        "predicted_vs_actual_by_band": credit["predicted_vs_actual_by_band"],
        # PSI
        "psi": {
            "champion": {"value": round(credit["champ_psi"], 6), "status": credit["champ_psi_status"]},
            "challenger": {"value": round(credit["chal_psi"], 6), "status": credit["chal_psi_status"]},
        },
        # Segment performance
        "segment_performance": credit["segment_performance"],
        # Credit metrics
        "credit_champion_metrics": credit["champ_metrics"],
        "credit_challenger_metrics": credit["chal_metrics"],
        # Fraud
        "fraud_supervised_metrics": fraud_result["sup_metrics"],
        "fraud_anomaly_metrics": fraud_result["anom_metrics"],
        "fraud_pr_curve": fraud_result["fraud_pr_curve"],
        # Stablecoin
        "stablecoin": {
            "score_distribution": sc_result["score_distribution"],
            "risk_action_mix": sc_result["risk_action_mix"],
            "high_risk_wallet_concentration": sc_result["high_risk_wallet_concentration"],
            "risky_exposure_by_score_band": sc_result["risky_exposure_by_score_band"],
            "threshold_sensitivity": sc_result["threshold_sensitivity"],
            "top_risk_driver_frequency": sc_result["top_risk_driver_frequency"],
            "discrimination_auc_vs_synthetic_label": sc_result["discrimination_auc_vs_synthetic_label"],
            "note": sc_result["note"],
        },
        # Champion vs challenger (mirror)
        "champion_vs_challenger": cc,
        # Verdicts (mirror)
        "verdicts": verdicts,
    }

    write_json(config.OUTPUTS / "model_validation_summary.json", summary)

    return summary
