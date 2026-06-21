"""Kaggle creditcard fraud ingest + synthetic labeled context.

Source: mlg-ulb/creditcardfraud — creditcard.csv (284,807 rows).
Real columns kept as-is: Time, V1..V28, Amount, Class (fraud_flag).

DOWNSAMPLING NOTE: The full 284k-row file exceeds GitHub's 100MB/file limit
when serialized to CSV with V-features. We deterministically downsample by
keeping ALL 492 fraud rows (Class==1) and seed-sampling legit rows (Class==0)
to reach config.PAYMENTS_SAMPLE_ROWS (80,000) total. This preserves the real
class imbalance (~0.6%) and all real fraud signal. The Time/Amount/V1..V28
values for kept rows are REAL and unaltered.

SYNTHETIC CONTEXT FIELDS: merchant_category, merchant_risk_band,
location_proxy, device_proxy, account_age_days, account_id are seeded-synthetic
and clearly labeled via is_synthetic_context=True on every row. The real labels
(fraud_flag) and real V-features are never altered.

Rolling behavioral features (transaction_count_24h, amount_count_24h) are
derived from the real Time ordering within each synthetic account, so they are
data-derived but account assignments are synthetic.

Deterministic: seeded via config.SEED throughout. Re-runs produce identical
output.
"""
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd

from src import config
from src.reporting import writers

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_RAW_FILE = "creditcard.csv"
_OUT_FILE = "processed_payment_transactions.csv"
_BASE_DT = datetime(2023, 1, 1, 0, 0, 0)  # epoch for Time (seconds elapsed)

_N_ACCOUNTS = 2000

_MERCHANT_CATEGORIES = [
    "retail", "grocery", "dining", "travel", "fuel",
    "entertainment", "healthcare", "online",
]
_RISK_BANDS = ["low", "medium", "high"]
_LOCATION_PROXIES = [f"REGION_{i:02d}" for i in range(1, 13)]  # 12 regions
_DEVICE_BUCKETS = [f"DEV_{i:04d}" for i in range(1, 51)]       # 50 device hash buckets

# Probabilities skewed so high-risk is rarer (realistic distribution)
_RISK_BAND_PROBS = [0.55, 0.35, 0.10]

_V_COLS = [f"V{i}" for i in range(1, 29)]

OUTPUT_COLUMNS = (
    ["transaction_id", "account_id", "transaction_time", "amount",
     "merchant_category", "merchant_risk_band", "location_proxy", "device_proxy",
     "account_age_days", "transaction_count_24h", "amount_count_24h",
     "fraud_flag", "chargeback_loss"]
    + _V_COLS
    + ["is_synthetic_context"]
)

# ---------------------------------------------------------------------------
# Download / cache
# ---------------------------------------------------------------------------

def _download() -> None:
    """Download creditcard.csv from Kaggle if not already present (cached).

    Uses ``dataset_download_files(..., unzip=True)`` so Kaggle handles
    extraction. Falls back to file-level download + manual zip extraction
    for partial caches. A valid plain-CSV at the target path short-circuits.
    """
    config.RAW.mkdir(parents=True, exist_ok=True)
    raw_csv = config.RAW / _RAW_FILE

    # If already present and is a real CSV (not a zip), we're done.
    if raw_csv.exists() and not zipfile.is_zipfile(raw_csv):
        return

    from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: PLC0415

    api = KaggleApi()
    api.authenticate()

    # Remove any corrupted/partial file before re-downloading.
    if raw_csv.exists():
        raw_csv.unlink()

    # download_files with unzip=True is the most reliable path for this dataset.
    api.dataset_download_files(
        config.KAGGLE_FRAUD, path=str(config.RAW), unzip=True
    )

    # Belt-and-suspenders: extract any residual .zip wrappers.
    for zp in config.RAW.glob("*.zip"):
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(config.RAW)
        zp.unlink()


# ---------------------------------------------------------------------------
# Core transformations
# ---------------------------------------------------------------------------

def _load_and_downsample(rng: np.random.Generator) -> pd.DataFrame:
    """Read creditcard.csv and deterministically downsample to PAYMENTS_SAMPLE_ROWS.

    All 492 fraud rows are kept unconditionally. Legit rows are seed-sampled
    to fill the remainder.
    """
    df = pd.read_csv(config.RAW / _RAW_FILE)

    fraud = df[df["Class"] == 1].copy()
    legit = df[df["Class"] == 0].copy()

    n_fraud = len(fraud)  # should be 492
    n_legit_target = config.PAYMENTS_SAMPLE_ROWS - n_fraud
    if len(legit) < n_legit_target:
        legit_sample = legit.copy()
    else:
        legit_idx = rng.choice(len(legit), size=n_legit_target, replace=False)
        legit_sample = legit.iloc[legit_idx].copy()

    combined = pd.concat([fraud, legit_sample], ignore_index=True)
    return combined


def _assign_accounts(n: int, rng: np.random.Generator) -> np.ndarray:
    """Seeded synthetic account assignment across _N_ACCOUNTS accounts."""
    return rng.integers(0, _N_ACCOUNTS, size=n)


def _make_transaction_times(time_seconds: pd.Series) -> pd.Series:
    """Convert elapsed seconds to ISO timestamp strings anchored at _BASE_DT."""
    base_ts = pd.Timestamp(_BASE_DT)
    times = base_ts + pd.to_timedelta(time_seconds, unit="s")
    return times.dt.strftime("%Y-%m-%dT%H:%M:%S")


def _rolling_24h_counts(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-account 24h rolling transaction count and above-median amount count.

    Rows must be sorted by transaction_time_sec (ascending) before calling.
    Both counts are inclusive of all transactions in the prior 24h window
    (i.e., strictly before the current transaction's time, within 86400s).

    amount_count_24h = count of prior-24h transactions where amount >
    per-account median amount. This is a defensible behavioral signal
    distinct from the raw count (captures high-value transaction density).
    If an account has fewer than 2 transactions, median is undefined and
    amount_count_24h == transaction_count_24h for those rows.
    """
    n = len(df)
    txn_count = np.zeros(n, dtype=np.int32)
    amt_count = np.zeros(n, dtype=np.int32)

    # Pre-compute per-account median amount (over the whole sample window).
    account_median = (
        df.groupby("_account_id_int")["amount"].median().to_dict()
    )

    # Group by account for efficient sliding window.
    for acct_id, grp in df.groupby("_account_id_int"):
        idxs = grp.index.to_numpy()
        times = grp["_time_sec"].to_numpy(dtype=np.float64)
        amounts = grp["amount"].to_numpy(dtype=np.float64)
        med_amt = account_median.get(acct_id, np.nan)
        if np.isnan(med_amt):
            med_amt = 0.0
        window_24h = 86400.0
        left = 0
        for right in range(len(idxs)):
            t_cur = times[right]
            # advance left pointer to keep window within 24h
            while times[left] <= t_cur - window_24h:
                left += 1
            # window is [left, right) — exclude current transaction
            window_amounts = amounts[left:right]
            txn_count[idxs[right]] = right - left
            amt_count[idxs[right]] = int(np.sum(window_amounts > med_amt))

    return txn_count, amt_count


def _build_synthetic_context(n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Generate all seeded-synthetic context fields."""
    ctx = pd.DataFrame(index=range(n))
    ctx["merchant_category"] = rng.choice(_MERCHANT_CATEGORIES, size=n)
    ctx["merchant_risk_band"] = rng.choice(
        _RISK_BANDS, size=n, p=_RISK_BAND_PROBS
    )
    ctx["location_proxy"] = rng.choice(_LOCATION_PROXIES, size=n)
    ctx["device_proxy"] = rng.choice(_DEVICE_BUCKETS, size=n)
    ctx["account_age_days"] = rng.integers(1, 3001, size=n)
    return ctx


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> pd.DataFrame:
    """Download, downsample, enrich, and write the payment transactions table.

    Returns the processed DataFrame (also written to
    data/processed/processed_payment_transactions.csv).
    """
    _download()

    rng = np.random.default_rng(config.SEED)

    raw = _load_and_downsample(rng)

    # Assign synthetic accounts (needed for time-ordering before rolling counts)
    account_ids_int = _assign_accounts(len(raw), rng)
    raw["_account_id_int"] = account_ids_int

    # Sort by time (ascending) for correct rolling windows; stable sort
    raw = raw.sort_values("Time", kind="stable").reset_index(drop=True)

    # Re-derive account ids after sort (they moved with rows)
    # Nothing to re-derive: _account_id_int already set per-row; sort moved rows
    # with their columns intact.

    # Build synthetic context (same rng, deterministic)
    ctx = _build_synthetic_context(len(raw), rng)

    # Rolling behavioral counts (requires sorted order + _account_id_int col)
    raw["_time_sec"] = raw["Time"].values.astype(np.float64)
    raw["amount"] = raw["Amount"].values

    txn_count, amt_count = _rolling_24h_counts(raw)

    # Assemble output frame
    out = pd.DataFrame()
    out["transaction_id"] = ["T" + str(i) for i in range(len(raw))]
    out["account_id"] = ["ACC" + str(x) for x in raw["_account_id_int"].values]
    out["transaction_time"] = _make_transaction_times(raw["Time"])
    out["amount"] = raw["Amount"].values
    out["merchant_category"] = ctx["merchant_category"].values
    out["merchant_risk_band"] = ctx["merchant_risk_band"].values
    out["location_proxy"] = ctx["location_proxy"].values
    out["device_proxy"] = ctx["device_proxy"].values
    out["account_age_days"] = ctx["account_age_days"].values
    out["transaction_count_24h"] = txn_count
    out["amount_count_24h"] = amt_count
    out["fraud_flag"] = raw["Class"].astype(int).values
    out["chargeback_loss"] = np.where(
        raw["Class"].values == 1, raw["Amount"].values, 0.0
    )

    # Real V-features (unaltered)
    for vcol in _V_COLS:
        out[vcol] = raw[vcol].values

    out["is_synthetic_context"] = True

    # Enforce column order
    out = out[OUTPUT_COLUMNS]

    # Sanity checks before write
    assert out["fraud_flag"].sum() == 492, (
        f"Expected 492 fraud rows; got {out['fraud_flag'].sum()}"
    )
    assert len(out) == config.PAYMENTS_SAMPLE_ROWS, (
        f"Expected {config.PAYMENTS_SAMPLE_ROWS} rows; got {len(out)}"
    )
    assert out["is_synthetic_context"].all(), "is_synthetic_context must be True for all rows"

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    writers.write_csv(config.PROCESSED / _OUT_FILE, out)

    return out
