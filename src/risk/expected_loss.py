"""Expected-loss engine (doc 05).

Translates model outputs into financial loss estimates:

* Credit:     Expected Loss = PD * LGD * EAD   (LGD/EAD assumptions labeled)
* Fraud:      Expected Fraud Loss = fraud_probability * amount * loss_severity
* Stablecoin: Risk Exposure proxy = stablecoin_risk_score * amount_usd

Plus segment views (with a hard RECONCILIATION gate — segment totals must equal
the portfolio total), Base/Moderate/Severe stress, and a policy loss comparison.
All LGD/EAD/severity/stress values are labeled assumptions, not observed losses.
"""
import numpy as np
import pandas as pd

from src import config
from src.reporting.writers import write_csv, write_json
from src.risk.underwriting import lgd_for, ead_for  # single source of LGD/EAD


class ReconciliationError(Exception):
    """Raised when segment loss totals do not reconcile to the portfolio total."""


# ---------------------------------------------------------------------------
# Core formulas
# ---------------------------------------------------------------------------
def credit_el(pd_, risk_grade, loan_amount, limit=None, revolving=False):
    """Credit expected loss = PD * LGD * EAD (doc 05 §3-5)."""
    lgd = lgd_for(risk_grade)
    ead = (float(limit) * config.UTILIZATION_ASSUMPTION) if revolving else ead_for(loan_amount)
    el = float(pd_) * lgd * ead
    return {
        "PD": float(pd_),
        "LGD": lgd,
        "EAD": ead,
        "expected_loss": el,
        "expected_loss_rate": (el / ead) if ead > 0 else 0.0,
    }


def fraud_el(fraud_probability, amount):
    """Expected fraud loss = p * amount * loss_severity (doc 05 §7)."""
    return max(0.0, float(fraud_probability) * float(amount) * config.FRAUD_LOSS_SEVERITY)


def stablecoin_exposure(score, amount_usd):
    """Stablecoin risk exposure proxy = score * amount_usd (doc 05 §8)."""
    return max(0.0, float(score) * float(amount_usd))


def _stress_loss(pd_arr, lgd_arr, ead_arr, scenario):
    """Vectorised stressed credit loss; PD and LGD capped at 1.0 (doc 05 §10)."""
    m = config.STRESS[scenario]
    pd_s = np.minimum(pd_arr * m["pd_mult"], 1.0)
    lgd_s = np.minimum(lgd_arr * m["lgd_mult"], 1.0)
    return pd_s * lgd_s * ead_arr


def _band_income(x):
    if pd.isna(x):
        return "unknown"
    if x < 40000:
        return "<40k"
    if x < 75000:
        return "40-75k"
    if x < 120000:
        return "75-120k"
    return "120k+"


def _band_dti(x):
    if pd.isna(x):
        return "unknown"
    if x < 10:
        return "<10"
    if x < 20:
        return "10-20"
    if x < 30:
        return "20-30"
    return "30+"


def _aggregate(df, by, loss_col="expected_loss", ead_col="EAD"):
    """Segment aggregation: total/avg loss, loss rate, count, exposure."""
    g = df.groupby(by, dropna=False)
    out = g.agg(
        total_expected_loss=(loss_col, "sum"),
        average_expected_loss=(loss_col, "mean"),
        account_count=(loss_col, "size"),
        exposure=(ead_col, "sum"),
    ).reset_index()
    out["expected_loss_rate"] = np.where(
        out["exposure"] > 0, out["total_expected_loss"] / out["exposure"], 0.0
    )
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build() -> dict:
    """Compute applicant-level EL, segments, stress, and policy comparison; write outputs."""
    dec = pd.read_csv(config.OUTPUTS / "underwriting_decisions.csv")
    model = pd.read_csv(
        config.PROCESSED / "underwriting_model_dataset.csv",
        usecols=["applicant_id", "annual_income", "debt_to_income", "credit_grade",
                 "loan_purpose", "application_vintage", "interest_rate", "loan_amount"],
    )
    df = dec.merge(model, on="applicant_id", how="left")

    # Segment dimension labels (fill NaN so every row is counted -> reconciles)
    df["loan_purpose"] = df["loan_purpose"].fillna("unknown")
    df["credit_grade"] = df["credit_grade"].fillna("unknown")
    df["application_vintage"] = df["application_vintage"].fillna("unknown")
    df["income_band"] = df["annual_income"].map(_band_income)
    df["debt_to_income_band"] = df["debt_to_income"].map(_band_dti)

    pd_arr = df["PD"].to_numpy()
    lgd_arr = df["LGD"].to_numpy()
    ead_arr = df["EAD"].to_numpy()

    # --- validation rules (doc 05 §14) ---
    assert ((pd_arr >= 0) & (pd_arr <= 1)).all(), "PD out of [0,1]"
    assert ((lgd_arr >= 0) & (lgd_arr <= 1)).all(), "LGD out of [0,1]"
    assert (ead_arr >= 0).all(), "EAD negative"
    assert (df["expected_loss"] >= 0).all(), "expected_loss negative"

    # --- stress (PD capped at 1) ---
    df["base_loss"] = _stress_loss(pd_arr, lgd_arr, ead_arr, "base")
    df["moderate_stress_loss"] = _stress_loss(pd_arr, lgd_arr, ead_arr, "moderate")
    df["severe_stress_loss"] = _stress_loss(pd_arr, lgd_arr, ead_arr, "severe")
    assert (df["severe_stress_loss"] >= df["moderate_stress_loss"] - 1e-9).all()
    assert (df["moderate_stress_loss"] >= df["base_loss"] - 1e-9).all()

    portfolio_el = float(df["expected_loss"].sum())

    # --- applicant-level output ---
    app_cols = ["applicant_id", "PD", "LGD", "EAD", "expected_loss", "expected_loss_rate",
                "base_loss", "moderate_stress_loss", "severe_stress_loss"]
    write_csv(config.OUTPUTS / "expected_loss_applicant_level.csv", df[app_cols])

    # --- segment views + RECONCILIATION gate ---
    seg_dims = ["risk_grade", "decision", "credit_grade", "loan_purpose",
                "income_band", "debt_to_income_band", "application_vintage"]
    segments = {}
    for dim in seg_dims:
        agg = _aggregate(df, dim)
        seg_total = float(agg["total_expected_loss"].sum())
        if abs(seg_total - portfolio_el) > 1e-6 * max(1.0, abs(portfolio_el)):
            raise ReconciliationError(
                f"segment '{dim}' total {seg_total} != portfolio {portfolio_el}")
        segments[dim] = agg.to_dict(orient="records")

    # --- fraud + stablecoin loss ---
    fraud = pd.read_csv(config.OUTPUTS / "fraud_alerts.csv")
    total_fraud_loss = float(fraud["expected_fraud_loss"].sum())
    fraud_loss_by_action = fraud.groupby("payment_action")["expected_fraud_loss"].sum().round(2).to_dict()

    stable = pd.read_csv(config.OUTPUTS / "stablecoin_alerts.csv")
    total_stablecoin_exposure = float(stable["risk_exposure_score"].sum())
    stablecoin_exposure_by_action = (
        stable.groupby("stablecoin_risk_action")["risk_exposure_score"].sum().round(2).to_dict())

    # --- expected_loss_by_segment.json ---
    write_json(config.OUTPUTS / "expected_loss_by_segment.json", {
        "credit_segments": segments,
        "fraud_loss_by_action": fraud_loss_by_action,
        "stablecoin_exposure_by_action": stablecoin_exposure_by_action,
        "portfolio_expected_credit_loss": round(portfolio_el, 2),
        "assumptions_note": "LGD by grade and EAD=loan_amount are labeled assumptions (doc 05).",
    })

    # --- expected_loss_summary.json (+ chart blocks) ---
    el_by_grade = df.groupby("risk_grade")["expected_loss"].sum().round(2).to_dict()
    el_by_decision = df.groupby("decision")["expected_loss"].sum().round(2).to_dict()
    write_json(config.OUTPUTS / "expected_loss_summary.json", {
        "total_expected_credit_loss": round(portfolio_el, 2),
        "total_expected_fraud_loss": round(total_fraud_loss, 2),
        "total_stablecoin_risk_exposure": round(total_stablecoin_exposure, 2),
        "average_pd": round(float(df["PD"].mean()), 6),
        "total_approved_exposure": round(float(df.loc[df["decision"] == "approve", "EAD"].sum()), 2),
        "expected_loss_by_risk_grade": el_by_grade,
        "expected_loss_by_decision": el_by_decision,
        "loss_waterfall": {
            "expected_credit_loss": round(portfolio_el, 2),
            "expected_fraud_loss": round(total_fraud_loss, 2),
            "stablecoin_risk_exposure": round(total_stablecoin_exposure, 2),
        },
        "assumptions": {
            "lgd_by_risk": config.LGD_BY_RISK, "utilization": config.UTILIZATION_ASSUMPTION,
            "fraud_loss_severity": config.FRAUD_LOSS_SEVERITY, "stress": config.STRESS,
            "note": "Assumption-driven estimates, not observed realized losses.",
        },
    })

    # --- stress_loss_summary.json (doc 05 §10) ---
    stress_summary = {}
    for sc_name in ["base", "moderate", "severe"]:
        col = "base_loss" if sc_name == "base" else f"{sc_name}_stress_loss"
        fmult = config.STRESS[sc_name]["fraud_mult"]
        stress_summary[sc_name] = {
            "expected_credit_loss": round(float(df[col].sum()), 2),
            "expected_fraud_loss": round(total_fraud_loss * fmult, 2),
            "stablecoin_risk_exposure": round(total_stablecoin_exposure, 2),
            "pd_multiplier": config.STRESS[sc_name]["pd_mult"],
            "lgd_multiplier": config.STRESS[sc_name]["lgd_mult"],
            "fraud_loss_multiplier": fmult,
        }
        stress_summary[sc_name]["total_expected_loss"] = round(
            stress_summary[sc_name]["expected_credit_loss"]
            + stress_summary[sc_name]["expected_fraud_loss"]
            + stress_summary[sc_name]["stablecoin_risk_exposure"], 2)
    write_json(config.OUTPUTS / "stress_loss_summary.json", {
        "scenarios": stress_summary,
        "note": "Simulated stress cases via PD/LGD/fraud multipliers; PD capped at 1.0.",
    })

    # --- policy_loss_comparison.json (doc 05 §11) ---
    # Vary approve cutoff (decline = 2x approve), including doc-reference and operating points.
    approve_cutoffs = sorted(set(
        [0.06, 0.10, config.PD_APPROVE, 0.20, 0.25, 0.30]))
    n = len(df)
    policies = []
    for ac in approve_cutoffs:
        dc = min(2 * ac, 0.6)
        approved = df["PD"] < ac
        declined = df["PD"] >= dc
        review = (~approved) & (~declined)
        approved_exposure = float(df.loc[approved, "EAD"].sum())
        ecl = float(df.loc[approved, "expected_loss"].sum())
        policies.append({
            "approve_cutoff": round(ac, 4),
            "decline_cutoff": round(dc, 4),
            "approval_rate": round(float(approved.mean()), 4),
            "review_rate": round(float(review.mean()), 4),
            "decline_rate": round(float(declined.mean()), 4),
            "approved_exposure": round(approved_exposure, 2),
            "expected_credit_loss": round(ecl, 2),
            "expected_fraud_loss": round(total_fraud_loss, 2),
            "stablecoin_risk_exposure": round(total_stablecoin_exposure, 2),
            "total_expected_loss": round(ecl + total_fraud_loss + total_stablecoin_exposure, 2),
            "loss_rate": round(ecl / approved_exposure, 6) if approved_exposure > 0 else 0.0,
        })
    write_json(config.OUTPUTS / "policy_loss_comparison.json", {
        "operating_point": {"approve": config.PD_APPROVE, "decline": config.PD_DECLINE},
        "doc_reference": config.DOC_REFERENCE_PD_THRESHOLDS,
        "policies": policies,
        "note": "Credit-policy loss/growth tradeoff; fraud + stablecoin held fixed across credit cutoffs.",
    })

    return {
        "portfolio_expected_credit_loss": round(portfolio_el, 2),
        "total_expected_fraud_loss": round(total_fraud_loss, 2),
        "total_stablecoin_risk_exposure": round(total_stablecoin_exposure, 2),
        "segments_reconciled": True,
    }
