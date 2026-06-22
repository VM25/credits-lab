"""Policy simulator data (doc 07).

Precomputes a grid of policy scenarios so the frontend can show real tradeoffs
(growth vs loss vs review burden vs fraud control) by looking up scenarios — no
fake recompute in the UI. Enforces constraint ordering and emits SPECIFIC,
quantified model-risk warnings (never "Risk is high.").

Scenario semantics (documented, labeled assumptions):
* expected_credit_loss = stressed EL on the APPROVED credit book.
* expected_fraud_loss  = stressed residual fraud loss LET THROUGH (fraud_score
  below the review/block threshold).
* stablecoin_risk_exposure = stressed exposure of wallets at/above the high-risk
  threshold.
* manual_review_volume = transactions flagged for manual review (>= fraud
  threshold), capped at review capacity (doc 04 §10).
"""
import numpy as np
import pandas as pd

from src import config
from src.reporting.writers import write_csv, write_json


# ---------------------------------------------------------------------------
# Constraint validation (doc 07 §10)
# ---------------------------------------------------------------------------
def valid_config(pd_approve=None, pd_decline=None, fraud_thresholds=None,
                 stablecoin_thresholds=None, multipliers=None, capacity=None) -> bool:
    """Return True iff the policy configuration satisfies the ordering/range rules."""
    if pd_approve is not None and pd_decline is not None:
        if not (0 <= pd_approve < pd_decline <= 1):
            return False
    if fraud_thresholds is not None:
        f = fraud_thresholds
        if not (f["approve"] < f["stepup"] < f["review"] < f["block"]):
            return False
        if not all(0 <= f[k] <= 1.01 for k in ("approve", "stepup", "review")):
            return False
    if stablecoin_thresholds is not None:
        s = stablecoin_thresholds
        if not (s["monitor"] < s["review"] < s["high_risk"]):
            return False
        if not all(0 <= s[k] <= 1 for k in s):
            return False
    if multipliers is not None and not all(m > 0 for m in multipliers):
        return False
    if capacity is not None and capacity < 0:
        return False
    return True


# ---------------------------------------------------------------------------
# Model-risk warnings (specific, quantified — doc 07 §9)
# ---------------------------------------------------------------------------
def warnings_for(review_volume, capacity, uncalibrated, verdict,
                 segment_loss_share=None, fp_increase_pct=None,
                 stablecoin_high_risk_share=None) -> list[str]:
    """Return a list of specific, quantified model-risk warnings."""
    w = []
    if capacity and review_volume > capacity:
        pct = round(100.0 * (review_volume - capacity) / capacity)
        w.append(f"Manual review volume exceeds capacity by {pct}%.")
    if uncalibrated:
        w.append("Policy uses uncalibrated PD; expected-loss figures are unreliable.")
    if verdict in ("Monitor", "Fail"):
        w.append(f"Underwriting champion validation verdict is {verdict}; decisions carry model risk.")
    if segment_loss_share is not None and segment_loss_share >= 0.40:
        w.append(f"Expected loss is concentrated: {round(100*segment_loss_share)}% sits in one risk grade.")
    if fp_increase_pct is not None and fp_increase_pct >= 25:
        w.append(f"Fraud false positives rise sharply (+{round(fp_increase_pct)}%) at this threshold.")
    if stablecoin_high_risk_share is not None and stablecoin_high_risk_share >= 0.15:
        w.append(f"High-risk stablecoin exposure increases to {round(100*stablecoin_high_risk_share)}% of wallets.")
    return w


# ---------------------------------------------------------------------------
# Grid definitions (discrete slider positions; frontend snaps to these)
# ---------------------------------------------------------------------------
_APPROVE_CUTOFFS = [0.06, 0.10, 0.15, 0.20, 0.25]   # 0.06 = doc reference
_REVIEW_BAND = 0.15                                  # decline = approve + band
_FRAUD_THRESHOLDS = [0.50, 0.60, 0.70, 0.80]         # manual-review boundary
_STABLECOIN_THRESHOLDS = [0.65, 0.75, 0.85]          # high-risk boundary
_STRESS = ["base", "moderate", "severe"]


def _control_inputs() -> dict:
    """Control definitions + defaults for the frontend sliders (doc 07 §3-6)."""
    return {
        "credit": {
            "approve_pd_cutoff": {"options": _APPROVE_CUTOFFS, "default": config.PD_APPROVE,
                                  "doc_reference": config.DOC_REFERENCE_PD_THRESHOLDS["approve"]},
            "review_band": {"value": _REVIEW_BAND, "note": "decline cutoff = approve cutoff + review band"},
            "decline_pd_cutoff_default": config.PD_DECLINE,
        },
        "fraud": {
            "review_threshold": {"options": _FRAUD_THRESHOLDS, "default": config.FRAUD_THRESHOLDS["review"]},
            "block_threshold": config.FRAUD_THRESHOLDS["block"],
            "manual_review_capacity": config.MANUAL_REVIEW_CAPACITY,
            "loss_severity": config.FRAUD_LOSS_SEVERITY,
        },
        "stablecoin": {
            "high_risk_threshold": {"options": _STABLECOIN_THRESHOLDS, "default": config.STABLECOIN_THRESHOLDS["high_risk"]},
            "monitor_threshold": config.STABLECOIN_THRESHOLDS["monitor"],
            "review_threshold": config.STABLECOIN_THRESHOLDS["review"],
        },
        "stress": {"options": _STRESS, "default": "base",
                   "multipliers": config.STRESS},
        "defaults": {"approve": config.PD_APPROVE, "decline": config.PD_DECLINE,
                     "fraud_review": config.FRAUD_THRESHOLDS["review"],
                     "stablecoin_high_risk": config.STABLECOIN_THRESHOLDS["high_risk"],
                     "stress": "base"},
    }


def build() -> dict:
    """Compute the scenario grid and write simulator inputs/results/grid."""
    cr = pd.read_csv(config.OUTPUTS / "underwriting_decisions.csv")  # PD, LGD, EAD, expected_loss
    fr = pd.read_csv(config.OUTPUTS / "fraud_alerts.csv")            # fraud_score, expected_fraud_loss
    st = pd.read_csv(config.OUTPUTS / "stablecoin_alerts.csv")       # stablecoin_risk_score, risk_exposure_score

    pd_arr = cr["PD"].to_numpy()
    lgd_arr = cr["LGD"].to_numpy()
    ead_arr = cr["EAD"].to_numpy()
    n_credit = len(cr)

    fscore = fr["fraud_score"].to_numpy()
    fefl = fr["expected_fraud_loss"].to_numpy()
    block_thr = config.FRAUD_THRESHOLDS["block"]

    sscore = st["stablecoin_risk_score"].to_numpy()
    sexp = st["risk_exposure_score"].to_numpy()

    # champion verdict drives a standing model-risk warning
    import json
    verdicts = json.load(open(config.OUTPUTS / "model_risk_verdicts.json"))
    vlist = verdicts if isinstance(verdicts, list) else verdicts.get("verdicts", verdicts)
    champ_verdict = next((v["validation_verdict"] for v in vlist
                          if v["model_name"] == "champion_scorecard"), "Pass")

    rows = []
    sid = 0
    for stress in _STRESS:
        m = config.STRESS[stress]
        pd_s = np.minimum(pd_arr * m["pd_mult"], 1.0)
        lgd_s = np.minimum(lgd_arr * m["lgd_mult"], 1.0)
        credit_loss_s = pd_s * lgd_s * ead_arr  # stressed EL per applicant
        for ac in _APPROVE_CUTOFFS:
            dc = min(ac + _REVIEW_BAND, 0.6)
            approved = pd_arr < ac
            review_c = (pd_arr >= ac) & (pd_arr < dc)
            declined = pd_arr >= dc
            ecl = float(credit_loss_s[approved].sum())
            for ft in _FRAUD_THRESHOLDS:
                flagged = fscore >= ft
                review_vol_raw = int(flagged.sum())
                review_vol = min(review_vol_raw, config.MANUAL_REVIEW_CAPACITY)
                blocked_rate = float((fscore >= block_thr).mean())
                # residual fraud loss let through (below review threshold), stressed
                efl = float(fefl[~flagged].sum()) * m["fraud_mult"]
                for sct in _STABLECOIN_THRESHOLDS:
                    high_risk = sscore >= sct
                    sexp_total = float(sexp[high_risk].sum())
                    total = ecl + efl + sexp_total
                    warns = warnings_for(
                        review_volume=review_vol_raw,
                        capacity=config.MANUAL_REVIEW_CAPACITY,
                        uncalibrated=False,
                        verdict=champ_verdict,
                        stablecoin_high_risk_share=float(high_risk.mean()),
                    )
                    rows.append({
                        "scenario_id": sid,
                        "stress_scenario": stress,
                        "credit_pd_cutoff": round(ac, 4),
                        "decline_pd_cutoff": round(dc, 4),
                        "fraud_threshold": round(ft, 4),
                        "stablecoin_threshold": round(sct, 4),
                        "approval_rate": round(float(approved.mean()), 4),
                        "review_rate": round(float(review_c.mean()), 4),
                        "decline_rate": round(float(declined.mean()), 4),
                        "expected_credit_loss": round(ecl, 2),
                        "expected_fraud_loss": round(efl, 2),
                        "stablecoin_risk_exposure": round(sexp_total, 2),
                        "total_expected_loss": round(total, 2),
                        "manual_review_volume": review_vol,
                        "blocked_transaction_rate": round(blocked_rate, 6),
                        "model_risk_flag": int(len(warns) > 0),
                        "model_risk_warnings": warns,
                    })
                    sid += 1

    grid = pd.DataFrame(rows)
    # CSV: the scalar columns (drop the list column)
    csv_cols = [c for c in grid.columns if c != "model_risk_warnings"]
    write_csv(config.OUTPUTS / "policy_threshold_grid.csv", grid[csv_cols])

    write_json(config.OUTPUTS / "policy_simulator_inputs.json", _control_inputs())
    write_json(config.OUTPUTS / "policy_simulator_results.json", {
        "scenarios": rows,
        "scenario_count": len(rows),
        "default_scenario": {
            "stress_scenario": "base",
            "credit_pd_cutoff": config.PD_APPROVE,
            "fraud_threshold": config.FRAUD_THRESHOLDS["review"],
            "stablecoin_threshold": config.STABLECOIN_THRESHOLDS["high_risk"],
        },
        "note": "Precomputed scenarios; the frontend looks up settings (no client-side risk recompute). Loss figures are assumption-driven estimates.",
    })

    return {"scenario_count": len(rows)}
