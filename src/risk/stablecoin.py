"""Stablecoin payments-risk module (SECONDARY).

Transparent wallet-risk scoring for stablecoin transactions. Payments-risk only —
no crypto trading, DeFi, NFT, yield, or token-price logic. The risk score is a
DOCUMENTED composite of AML-style risk indicators (not a trained classifier);
the synthetic ``stablecoin_risk_label`` in the data is reserved for validation
(Phase 7) and is never an input to the score.

Language: "AML-style risk indicators" only — never "AML compliance".
"""
import json

import numpy as np
import pandas as pd

from src import config
from src.reporting.writers import write_csv, write_json

# Composite weights (sum to 1.0 → score naturally in [0,1]).
_W = {
    "counterparty_risk": 0.40,
    "risky_exposure": 0.20,
    "velocity": 0.15,
    "large_transfer": 0.10,
    "new_counterparty": 0.10,
    "imbalanced_flow": 0.05,
}

# Reason thresholds (per-row, no global context needed).
_HIGH_COUNTERPARTY = 0.70
_HIGH_VELOCITY = 10.0
_IMBALANCED_RATIO_HI = 3.0
_IMBALANCED_RATIO_LO = 1.0 / 3.0

ALLOWED_REASONS = {
    "high_counterparty_risk": "Counterparty wallet carries an elevated risk score (AML-style indicator).",
    "risky_address_exposure": "Wallet has exposure to a flagged risky address (AML-style indicator).",
    "high_wallet_velocity": "Wallet transaction velocity is unusually high over the recent window.",
    "large_transfer": "Transfer amount is in the large-transfer tail for the sample.",
    "new_counterparty": "First observed transfer between this wallet and counterparty.",
    "imbalanced_flow": "Inflow and outflow are strongly imbalanced (possible layering pattern).",
}

OUTPUT_COLUMNS = [
    "wallet_id", "counterparty_wallet_id", "transaction_time", "amount_usd",
    "stablecoin_risk_score", "stablecoin_risk_action", "risk_exposure_score",
    "top_reason_1", "top_reason_2", "top_reason_3",
]


def action(score: float) -> str:
    """Map a stablecoin risk score to an action (doc 04 §8)."""
    t = config.STABLECOIN_THRESHOLDS
    if score < t["monitor"]:
        return "normal"
    if score < t["review"]:
        return "monitor"
    if score < t["high_risk"]:
        return "review"
    return "high_risk"


def _imbalanced_flow_signal(ratio):
    """High when inflow/outflow ratio is far from balanced; in [0,1]."""
    r = np.asarray(ratio, dtype=float)
    sig = np.abs(np.log10(np.clip(r, 1e-9, None))) / 2.0
    return np.clip(sig, 0.0, 1.0)


def reason_codes(row) -> list[str]:
    """Top 1-3 triggered AML-style indicator codes for a wallet transaction."""
    codes = []
    if float(row.get("counterparty_risk_score", 0) or 0) > _HIGH_COUNTERPARTY:
        codes.append("high_counterparty_risk")
    if int(row.get("risky_address_exposure_flag", 0) or 0) == 1:
        codes.append("risky_address_exposure")
    if float(row.get("wallet_velocity", 0) or 0) > _HIGH_VELOCITY:
        codes.append("high_wallet_velocity")
    if int(row.get("large_transfer_flag", 0) or 0) == 1:
        codes.append("large_transfer")
    if int(row.get("new_counterparty_flag", 0) or 0) == 1:
        codes.append("new_counterparty")
    ratio = float(row.get("inflow_outflow_ratio", 1.0) or 1.0)
    if ratio > _IMBALANCED_RATIO_HI or ratio < _IMBALANCED_RATIO_LO:
        codes.append("imbalanced_flow")
    return codes[:3]


def score_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features + ``stablecoin_risk_score`` + ``risk_exposure_score``."""
    out = df.copy()
    out["transaction_time"] = pd.to_datetime(out["transaction_time"], errors="coerce")
    out = out.sort_values(["wallet_id", "transaction_time"], kind="stable").reset_index(drop=True)

    # Engineered features (doc 02 §6 / 04 §4)
    out["wallet_velocity"] = out["transaction_count_24h"].astype(float)
    out["inflow_outflow_ratio"] = out["inflow_24h"] / (out["outflow_24h"] + 1.0)
    # per-wallet share of transfers to its most-frequent counterparty
    def _concentration(g):
        vc = g.value_counts()
        return vc.iloc[0] / len(g) if len(g) else 0.0
    conc = out.groupby("wallet_id")["counterparty_wallet_id"].transform(
        lambda s: s.map(s.value_counts()) / len(s)
    )
    out["counterparty_concentration"] = conc.astype(float)
    denom = (out["inflow_24h"] + out["outflow_24h"] + 1.0)
    out["round_trip_proxy"] = (1.0 - (out["inflow_24h"] - out["outflow_24h"]).abs() / denom).clip(0, 1)
    amt_hi = out["amount_usd"].quantile(0.95)
    out["large_transfer_flag"] = (out["amount_usd"] > amt_hi).astype(int)
    out["new_counterparty_flag"] = (
        ~out.duplicated(subset=["wallet_id", "counterparty_wallet_id"], keep="first")
    ).astype(int)

    # Normalized velocity for scoring
    vel_hi = out["wallet_velocity"].quantile(0.95)
    norm_vel = (out["wallet_velocity"] / vel_hi).clip(0, 1) if vel_hi > 0 else out["wallet_velocity"] * 0.0

    # Composite score (weights sum to 1.0; label is NEVER used as input)
    out["stablecoin_risk_score"] = (
        _W["counterparty_risk"] * out["counterparty_risk_score"].astype(float)
        + _W["risky_exposure"] * out["risky_address_exposure_flag"].astype(float)
        + _W["velocity"] * norm_vel
        + _W["large_transfer"] * out["large_transfer_flag"].astype(float)
        + _W["new_counterparty"] * out["new_counterparty_flag"].astype(float)
        + _W["imbalanced_flow"] * _imbalanced_flow_signal(out["inflow_outflow_ratio"])
    ).clip(0.0, 1.0)

    # Risk exposure proxy (doc 05 §8): score * amount
    out["risk_exposure_score"] = (out["stablecoin_risk_score"] * out["amount_usd"]).clip(lower=0.0)
    return out


def build() -> dict:
    """Score the stablecoin sample, derive actions/reasons, and write outputs."""
    df = pd.read_csv(config.PROCESSED / "processed_stablecoin_transactions.csv")
    scored = score_frame(df)
    scored["stablecoin_risk_action"] = scored["stablecoin_risk_score"].apply(action)

    reasons = scored.apply(reason_codes, axis=1)
    for i in range(3):
        scored[f"top_reason_{i+1}"] = reasons.apply(lambda c, i=i: c[i] if len(c) > i else None)

    scored["transaction_time"] = scored["transaction_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    write_csv(config.OUTPUTS / "stablecoin_alerts.csv", scored[OUTPUT_COLUMNS])

    # Summary blocks (doc 08 §8)
    action_mix = scored["stablecoin_risk_action"].value_counts().to_dict()
    high_risk_wallet_count = int((scored["stablecoin_risk_action"] == "high_risk").sum())
    risk_exposure_by_action = (
        scored.groupby("stablecoin_risk_action")["risk_exposure_score"].sum().round(2).to_dict()
    )
    driver_counts: dict[str, int] = {}
    for col in ["top_reason_1", "top_reason_2", "top_reason_3"]:
        for v in scored[col].dropna():
            driver_counts[v] = driver_counts.get(v, 0) + 1
    top_wallet_risk_drivers = dict(sorted(driver_counts.items(), key=lambda x: -x[1]))

    lb = (
        scored.groupby("wallet_id")
        .agg(total_exposure=("risk_exposure_score", "sum"),
             max_score=("stablecoin_risk_score", "max"),
             n_tx=("stablecoin_risk_score", "count"))
        .sort_values("total_exposure", ascending=False)
        .head(15)
        .reset_index()
    )
    wallet_risk_leaderboard = lb.to_dict(orient="records")

    payload = {
        "rows": json.loads(scored[OUTPUT_COLUMNS].to_json(orient="records")),
        "row_count_total": int(len(scored)),
        "data_note": "Synthetic stablecoin transaction sample. Scores reflect AML-style risk indicators only.",
        "action_mix": action_mix,
        "high_risk_wallet_count": high_risk_wallet_count,
        "risk_exposure_by_action": risk_exposure_by_action,
        "top_wallet_risk_drivers": top_wallet_risk_drivers,
        "wallet_risk_leaderboard": wallet_risk_leaderboard,
    }
    write_json(config.OUTPUTS / "stablecoin_alerts.json", payload)

    return {
        "action_mix": action_mix,
        "high_risk_wallet_count": high_risk_wallet_count,
        "row_count_total": int(len(scored)),
    }
