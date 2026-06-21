"""Synthetic stablecoin transaction ingest — payments-risk extension.

All data is fully synthetic (seeded via config.SEED). Every row is flagged
is_synthetic=True. No real transaction data, no crypto-price/DeFi/NFT/yield
logic — this module generates raw doc-02 §6 fields only. Engineered features
(wallet_velocity, inflow_outflow_ratio, etc.) are derived downstream in the
stablecoin risk module.

Label construction rationale:
  stablecoin_risk_label is a synthetic binary label correlated with high
  counterparty_risk_score, risky_address_exposure_flag, and high
  transaction_count_24h (velocity). Noise is added so no single field
  perfectly predicts the label — downstream scorers must learn combinations.
  Target imbalance: ~10–15% positive.

Deterministic: seeded via config.SEED. Re-runs produce identical output.
"""

import numpy as np
import pandas as pd

from src import config
from src.reporting import writers

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_OUT_FILE = "processed_stablecoin_transactions.csv"

_N_WALLETS = 800
_TOKEN_TYPES = ["USDT", "USDC", "DAI", "BUSD"]
_TOKEN_PROBS = [0.45, 0.30, 0.15, 0.10]

# 90-day window ending at a fixed reference date
_WINDOW_DAYS = 90
_REF_DATE = pd.Timestamp("2026-03-21")  # end of window

OUTPUT_COLUMNS = [
    "wallet_id",
    "counterparty_wallet_id",
    "transaction_time",
    "token_type",
    "amount_usd",
    "wallet_age_days",
    "inflow_24h",
    "outflow_24h",
    "transaction_count_24h",
    "counterparty_risk_score",
    "risky_address_exposure_flag",
    "stablecoin_risk_label",
    "is_synthetic",
]


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def _make_wallet_ids(rng: np.random.Generator, n: int, n_wallets: int, prefix: str) -> np.ndarray:
    """Generate wallet ID strings (e.g. 'W0042') drawn uniformly from n_wallets."""
    ids = rng.integers(0, n_wallets, size=n)
    return np.array([f"{prefix}{i:04d}" for i in ids])


def _make_transaction_times(rng: np.random.Generator, n: int) -> np.ndarray:
    """Spread n transactions uniformly over a _WINDOW_DAYS window ending at _REF_DATE."""
    start = _REF_DATE - pd.Timedelta(days=_WINDOW_DAYS)
    total_seconds = int(_WINDOW_DAYS * 86400)
    offsets = rng.integers(0, total_seconds, size=n)
    times = start + pd.to_timedelta(offsets, unit="s")
    # Return ISO strings (no timezone suffix — consistent with other ingests)
    return times.strftime("%Y-%m-%dT%H:%M:%S").to_numpy()


def _make_amount_usd(rng: np.random.Generator, n: int) -> np.ndarray:
    """Lognormal amounts with heavy tail; guaranteed > 0.

    mu=6 (≈$400 median), sigma=2 gives heavy tail up to ~$1M+.
    Clip floor at 0.01 to ensure strict positivity (lognormal is always >0
    by definition, but clip guards against any floating-point edge cases).
    """
    amounts = rng.lognormal(mean=6.0, sigma=2.0, size=n)
    return np.clip(amounts, 0.01, None)


def _make_counterparty_risk_score(rng: np.random.Generator, n: int) -> np.ndarray:
    """Counterparty risk score in [0, 1].

    Mix of a low-risk beta and a high-risk uniform component to create a
    realistic bimodal distribution. Clipped to [0, 1].
    """
    # 80% low-risk (beta skewed left), 20% elevated-risk (uniform)
    mask_high = rng.random(n) < 0.20
    scores = np.where(
        mask_high,
        rng.uniform(0.5, 1.0, size=n),
        rng.beta(2.0, 8.0, size=n),
    )
    return np.clip(scores, 0.0, 1.0)


def _make_risky_exposure_flag(
    rng: np.random.Generator, counterparty_risk: np.ndarray
) -> np.ndarray:
    """Binary flag correlated with high counterparty risk score.

    P(flag=1) = 0.05 + 0.70 * counterparty_risk  (clamped to [0,1]).
    """
    probs = np.clip(0.05 + 0.70 * counterparty_risk, 0.0, 1.0)
    return (rng.random(len(counterparty_risk)) < probs).astype(int)


def _make_velocity_fields(rng: np.random.Generator, n: int) -> tuple:
    """Inflow, outflow, and transaction_count_24h.

    inflow_24h and outflow_24h: lognormal, non-negative.
    transaction_count_24h: small int (Poisson-ish via integers).
    """
    inflow = np.clip(rng.lognormal(mean=5.0, sigma=1.5, size=n), 0.0, None)
    outflow = np.clip(rng.lognormal(mean=4.8, sigma=1.5, size=n), 0.0, None)
    txn_count = rng.integers(1, 30, size=n)  # 1..29 inclusive
    return inflow, outflow, txn_count


def _make_wallet_age(rng: np.random.Generator, n: int) -> np.ndarray:
    """Wallet age in days, 1–1500 inclusive."""
    return rng.integers(1, 1501, size=n)


def _make_risk_label(
    rng: np.random.Generator,
    counterparty_risk: np.ndarray,
    risky_flag: np.ndarray,
    txn_count: np.ndarray,
) -> np.ndarray:
    """Synthetic binary risk label correlated with multiple risk signals.

    Base probability from a weighted combination of signals, with additive
    noise so no single column trivially determines the label. Target ~10-15%
    positive rate.

    Formula:
        p = sigmoid( -3.5
                     + 4.5 * counterparty_risk
                     + 2.0 * risky_flag
                     + 0.08 * log1p(txn_count)
                     + noise )
    where noise ~ N(0, 0.5) adds irreducible variance.
    """
    noise = rng.normal(0, 0.5, size=len(counterparty_risk))
    logit = (
        -4.8
        + 4.5 * counterparty_risk
        + 2.0 * risky_flag.astype(float)
        + 0.08 * np.log1p(txn_count.astype(float))
        + noise
    )
    probs = 1.0 / (1.0 + np.exp(-logit))
    return (rng.random(len(probs)) < probs).astype(int)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> pd.DataFrame:
    """Generate synthetic stablecoin transaction data and write processed CSV.

    Returns the processed DataFrame (also written to
    data/processed/processed_stablecoin_transactions.csv).
    """
    n = config.STABLECOIN_ROWS
    rng = np.random.default_rng(config.SEED)

    # Core identifiers
    wallet_ids = _make_wallet_ids(rng, n, _N_WALLETS, "W")
    counterparty_ids = _make_wallet_ids(rng, n, _N_WALLETS, "W")

    # Temporal
    transaction_times = _make_transaction_times(rng, n)

    # Token type
    token_types = rng.choice(_TOKEN_TYPES, size=n, p=_TOKEN_PROBS)

    # Amounts
    amount_usd = _make_amount_usd(rng, n)

    # Wallet age
    wallet_age_days = _make_wallet_age(rng, n)

    # Velocity fields
    inflow_24h, outflow_24h, txn_count_24h = _make_velocity_fields(rng, n)

    # Risk scores and flags
    counterparty_risk_score = _make_counterparty_risk_score(rng, n)
    risky_address_exposure_flag = _make_risky_exposure_flag(rng, counterparty_risk_score)

    # Synthetic risk label
    stablecoin_risk_label = _make_risk_label(
        rng, counterparty_risk_score, risky_address_exposure_flag, txn_count_24h
    )

    # Assemble DataFrame
    df = pd.DataFrame({
        "wallet_id": wallet_ids,
        "counterparty_wallet_id": counterparty_ids,
        "transaction_time": transaction_times,
        "token_type": token_types,
        "amount_usd": amount_usd,
        "wallet_age_days": wallet_age_days,
        "inflow_24h": inflow_24h,
        "outflow_24h": outflow_24h,
        "transaction_count_24h": txn_count_24h,
        "counterparty_risk_score": counterparty_risk_score,
        "risky_address_exposure_flag": risky_address_exposure_flag,
        "stablecoin_risk_label": stablecoin_risk_label,
        "is_synthetic": True,
    })

    # Enforce column order
    df = df[OUTPUT_COLUMNS]

    # Sanity checks before write
    assert (df["amount_usd"] > 0).all(), "amount_usd must be strictly positive"
    assert df["counterparty_risk_score"].between(0, 1).all(), "risk score out of [0,1]"
    assert set(df["stablecoin_risk_label"].unique()) <= {0, 1}, "label must be 0/1"
    assert set(df["risky_address_exposure_flag"].unique()) <= {0, 1}, "flag must be 0/1"
    assert df["is_synthetic"].all(), "is_synthetic must be True for all rows"
    assert len(df) == n, f"Expected {n} rows; got {len(df)}"

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    writers.write_csv(config.PROCESSED / _OUT_FILE, df)

    # Print summary stats
    pos_rate = df["stablecoin_risk_label"].mean()
    risky_rate = df["risky_address_exposure_flag"].mean()
    print(f"[ingest_stablecoin] rows={len(df):,}  "
          f"label_positive_rate={pos_rate:.3f}  "
          f"risky_exposure_rate={risky_rate:.3f}")

    return df
