"""LendingClub credit ingest — accepted + rejected applicants.

Produces data/processed/processed_credit_applicants.csv with an
application-time-only schema plus a default PROXY target.

LEAKAGE IS A HARD STOP CONDITION. The accepted file has 151 columns, most of
which describe post-origination behavior (payments, recoveries, last/next
payment dates, outstanding principal, etc.). We defend against leakage by
reading ONLY an explicit application-time whitelist (`_ACCEPTED_USECOLS`) in
chunks, and by DROPPING raw `loan_status` after deriving the target. No
post-origination / future-outcome field may appear in the output.

default_flag is a default / severe-delinquency PROXY derived from loan_status
(labeled as such in methodology downstream). Rejected applicants have no
observed outcome, so default_flag is NaN for them; they exist for the approval
funnel / policy / reject-inference only and must never be used for supervised
PD training (that filtering happens later in features.py).

Downloads are cached under data/raw/; an existing file is reused.
"""
import zipfile

import numpy as np
import pandas as pd

from src import config
from src.reporting import writers

ACCEPTED_FILE = "accepted_2007_to_2018Q4.csv.gz"
REJECTED_FILE = "rejected_2007_to_2018Q4.csv.gz"

# ---------------------------------------------------------------------------
# Leakage defense: read ONLY these application-time columns from the accepted
# file. loan_status is included solely to derive the target and is dropped
# before output. Everything else in the 151-column file (payments, recoveries,
# outstanding balances, last/next payment dates, etc.) is intentionally never
# loaded.
# ---------------------------------------------------------------------------
_ACCEPTED_USECOLS = [
    "issue_d",         # -> application_date
    "loan_amnt",       # -> loan_amount
    "annual_inc",      # -> annual_income
    "dti",             # -> debt_to_income
    "emp_length",      # -> employment_length
    "grade",           # -> credit_grade
    "int_rate",        # -> interest_rate
    "purpose",         # -> loan_purpose
    "home_ownership",  # -> home_ownership
    "delinq_2yrs",     # -> delinquency_history
    "revol_util",      # -> revolving_utilization
    "open_acc",        # -> open_accounts
    "loan_status",     # -> default_flag (DROPPED after derivation)
]

# loan_status -> default proxy mapping
_DEFAULT_STATUSES = {
    "Charged Off",
    "Default",
    "Late (31-120 days)",
    "Does not meet the credit policy. Status:Charged Off",
}
_PAID_STATUSES = {"Fully Paid"}
# Statuses kept for the supervised label; all others are ambiguous / in-progress
# (Current, In Grace Period, Late (16-30 days), Issued, etc.) and are dropped.
_KEEP_STATUSES = _DEFAULT_STATUSES | _PAID_STATUSES

# Final output column order.
OUTPUT_COLUMNS = [
    "applicant_id",
    "application_date",
    "loan_amount",
    "annual_income",
    "debt_to_income",
    "employment_length",
    "credit_grade",
    "interest_rate",
    "loan_purpose",
    "home_ownership",
    "delinquency_history",
    "revolving_utilization",
    "open_accounts",
    "default_flag",
    "loss_amount_if_default",
    "applicant_type",
    "is_synthetic_reject",
]

# Any of these in the output would be a leakage failure. Asserted before write.
_LEAK_COLUMNS = {
    "recoveries", "collection_recovery_fee", "total_pymnt", "total_rec_prncp",
    "total_rec_int", "last_pymnt_d", "last_pymnt_amnt", "out_prncp",
    "next_pymnt_d", "loan_status",
}

N_REJECT_REAL = 20000
N_REJECT_SYNTHETIC = 5000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _download():
    """Ensure both LendingClub files exist under data/raw/ (cached).

    Kaggle may deliver a file directly as .csv.gz or wrapped in a .zip. We
    download only what is missing and extract any .zip we find.
    """
    config.RAW.mkdir(parents=True, exist_ok=True)
    want = [ACCEPTED_FILE, REJECTED_FILE]

    if all((config.RAW / fn).exists() for fn in want):
        return

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    for fn in want:
        if (config.RAW / fn).exists():
            continue
        api.dataset_download_file(config.KAGGLE_CREDIT, fn, path=str(config.RAW))

    # Extract any zip wrappers Kaggle may have produced.
    for zp in config.RAW.glob("*.zip"):
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(config.RAW)


def _parse_emp_length(series: pd.Series) -> pd.Series:
    """Parse LendingClub emp_length text to numeric years.

    "10+ years"->10, "< 1 year"->0, "n/a"/NaN->NaN, "3 years"->3.
    """
    s = series.astype("string").str.strip()
    out = pd.Series(np.nan, index=series.index, dtype="float64")
    out[s == "10+ years"] = 10.0
    out[s == "< 1 year"] = 0.0
    # "N years" / "N year" for the remaining rows
    digits = s.str.extract(r"^(\d+)\s*years?$", expand=False)
    mask = digits.notna()
    out[mask] = digits[mask].astype("float64")
    return out


def _strip_pct(series: pd.Series) -> pd.Series:
    """Coerce a possibly-"%"-suffixed column to float.

    This dataset stores int_rate / revol_util as plain floats, but other
    columns (and other releases) carry a "%" suffix; handle both.
    """
    if pd.api.types.is_numeric_dtype(series):
        return series.astype("float64")
    s = series.astype("string").str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce")


def _derive_default_flag(loan_status: pd.Series) -> pd.Series:
    """Map kept loan statuses to {1.0, 0.0}; others -> NaN (caller drops them)."""
    flag = pd.Series(np.nan, index=loan_status.index, dtype="float64")
    flag[loan_status.isin(_DEFAULT_STATUSES)] = 1.0
    flag[loan_status.isin(_PAID_STATUSES)] = 0.0
    return flag


def _read_accepted_kept() -> pd.DataFrame:
    """Read accepted file in chunks (application-time usecols only), keeping only
    label-resolvable rows, and derive default_flag + issue year."""
    path = config.RAW / ACCEPTED_FILE
    frames = []
    reader = pd.read_csv(
        path,
        compression="gzip",
        usecols=_ACCEPTED_USECOLS,
        chunksize=200_000,
        low_memory=False,
    )
    for chunk in reader:
        chunk = chunk[chunk["loan_status"].isin(_KEEP_STATUSES)].copy()
        if chunk.empty:
            continue
        chunk["default_flag"] = _derive_default_flag(chunk["loan_status"])
        issue = pd.to_datetime(chunk["issue_d"], format="%b-%Y", errors="coerce")
        chunk["_issue_dt"] = issue
        chunk["_issue_year"] = issue.dt.year
        # Need a usable year for stratification / time-aware splits.
        chunk = chunk.dropna(subset=["_issue_year"])
        frames.append(chunk)

    accepted = pd.concat(frames, ignore_index=True)
    accepted["_issue_year"] = accepted["_issue_year"].astype(int)
    return accepted


def _stratified_sample(accepted: pd.DataFrame, n_target: int) -> pd.DataFrame:
    """Seeded, proportional stratified sample by (issue year, default_flag).

    Preserves each vintage and the year/status distribution so downstream
    time-aware splits keep usable rows per year.
    """
    n_total = len(accepted)
    if n_total <= n_target:
        return accepted.copy()
    frac = n_target / n_total
    pieces = []
    for _, g in accepted.groupby(["_issue_year", "default_flag"], group_keys=False):
        pieces.append(g.sample(n=max(1, round(len(g) * frac)), random_state=config.SEED))
    sampled = pd.concat(pieces)
    return sampled.reset_index(drop=True)


def _map_accepted(accepted: pd.DataFrame) -> pd.DataFrame:
    """Map sampled accepted rows to the output schema."""
    out = pd.DataFrame(index=accepted.index)
    # Stable generated id (preferred over LC id, which we don't load).
    out["applicant_id"] = ["A" + str(i) for i in accepted.index]
    out["application_date"] = accepted["_issue_dt"].dt.strftime("%Y-%m-%d")
    out["loan_amount"] = pd.to_numeric(accepted["loan_amnt"], errors="coerce")
    out["annual_income"] = pd.to_numeric(accepted["annual_inc"], errors="coerce")
    out["debt_to_income"] = pd.to_numeric(accepted["dti"], errors="coerce")
    out["employment_length"] = _parse_emp_length(accepted["emp_length"])
    out["credit_grade"] = accepted["grade"]
    out["interest_rate"] = _strip_pct(accepted["int_rate"])
    out["loan_purpose"] = accepted["purpose"]
    out["home_ownership"] = accepted["home_ownership"]
    out["delinquency_history"] = pd.to_numeric(accepted["delinq_2yrs"], errors="coerce")
    out["revolving_utilization"] = _strip_pct(accepted["revol_util"])
    out["open_accounts"] = pd.to_numeric(accepted["open_acc"], errors="coerce")
    out["default_flag"] = accepted["default_flag"].values
    # ASSUMPTION (labeled): flat portfolio LGD = config.LGD_DEFAULT. Precise
    # per-grade LGD is applied later in the expected-loss engine (doc 05).
    out["loss_amount_if_default"] = out["loan_amount"] * config.LGD_DEFAULT
    out["applicant_type"] = "accepted"
    out["is_synthetic_reject"] = False
    return out


def _empty_required(n: int, index) -> pd.DataFrame:
    """Frame of all required columns set to NaN (for reject rows)."""
    cols = [c for c in OUTPUT_COLUMNS if c not in ("applicant_type", "is_synthetic_reject")]
    return pd.DataFrame({c: np.full(n, np.nan) for c in cols}, index=index)


def _map_rejects_real() -> pd.DataFrame:
    """Sample real rejected applicants and map the fields that exist.

    Rejects have no observed outcome -> default_flag = NaN.
    """
    path = config.RAW / REJECTED_FILE
    usecols = [
        "Amount Requested", "Application Date", "Loan Title",
        "Debt-To-Income Ratio", "Employment Length",
    ]
    rej = pd.read_csv(path, compression="gzip", usecols=usecols, low_memory=False)
    if len(rej) > N_REJECT_REAL:
        rej = rej.sample(n=N_REJECT_REAL, random_state=config.SEED)
    rej = rej.reset_index(drop=True)

    out = _empty_required(len(rej), rej.index)
    out["applicant_id"] = ["RR" + str(i) for i in rej.index]
    out["loan_amount"] = pd.to_numeric(rej["Amount Requested"], errors="coerce")
    out["application_date"] = pd.to_datetime(
        rej["Application Date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    out["debt_to_income"] = _strip_pct(rej["Debt-To-Income Ratio"])
    out["employment_length"] = _parse_emp_length(rej["Employment Length"])
    out["loan_purpose"] = rej["Loan Title"]
    out["default_flag"] = np.nan
    out["loss_amount_if_default"] = np.nan
    out["applicant_type"] = "rejected_real"
    out["is_synthetic_reject"] = False
    return out


def _map_rejects_synthetic(n: int = N_REJECT_SYNTHETIC) -> pd.DataFrame:
    """Generate clearly-labeled synthetic rejected applicants (seeded).

    For reject-inference / policy context only. Plausible distributions; no
    observed outcome (default_flag = NaN). NEVER used for supervised PD.
    """
    rng = np.random.default_rng(config.SEED)
    idx = pd.RangeIndex(n)
    out = _empty_required(n, idx)

    out["applicant_id"] = ["RS" + str(i) for i in range(n)]
    # Span the LC vintage window for time-aware context.
    start = np.datetime64("2007-01-01")
    days = rng.integers(0, 365 * 12, size=n)
    dates = start + days.astype("timedelta64[D]")
    out["application_date"] = pd.to_datetime(dates).strftime("%Y-%m-%d")
    out["loan_amount"] = np.round(rng.uniform(1000, 40000, size=n), -2)
    out["annual_income"] = np.round(rng.lognormal(mean=10.8, sigma=0.5, size=n), -2)
    # Rejects skew to weaker credit: higher DTI, thinner files.
    out["debt_to_income"] = np.round(rng.uniform(15, 60, size=n), 2)
    out["employment_length"] = rng.integers(0, 11, size=n).astype("float64")
    out["credit_grade"] = rng.choice(list("DEFG"), size=n)
    out["interest_rate"] = np.round(rng.uniform(12, 31, size=n), 2)
    out["loan_purpose"] = rng.choice(
        ["debt_consolidation", "credit_card", "other", "small_business",
         "medical", "home_improvement"],
        size=n,
    )
    out["home_ownership"] = rng.choice(["RENT", "MORTGAGE", "OWN"], size=n)
    out["delinquency_history"] = rng.integers(0, 6, size=n).astype("float64")
    out["revolving_utilization"] = np.round(rng.uniform(30, 110, size=n), 1)
    out["open_accounts"] = rng.integers(1, 25, size=n).astype("float64")
    out["default_flag"] = np.nan
    out["loss_amount_if_default"] = np.nan
    out["applicant_type"] = "rejected_synthetic"
    out["is_synthetic_reject"] = True
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run() -> pd.DataFrame:
    """Build, validate, and write the combined credit-applicant table."""
    _download()

    accepted_all = _read_accepted_kept()
    accepted_sampled = _stratified_sample(accepted_all, config.CREDIT_SAMPLE_ROWS)
    accepted_out = _map_accepted(accepted_sampled)

    rejects_real = _map_rejects_real()
    rejects_syn = _map_rejects_synthetic()

    combined = pd.concat(
        [accepted_out, rejects_real, rejects_syn], ignore_index=True
    )
    combined = combined[OUTPUT_COLUMNS]

    # default_flag stays integer-valued where present; NaN for rejects forces
    # float dtype, which is correct (NaN cannot live in an int column).
    combined["default_flag"] = combined["default_flag"].astype("float64")
    combined["is_synthetic_reject"] = combined["is_synthetic_reject"].astype(bool)

    # --- Leakage hard stop: no post-origination field may be present. ---
    leaked = _LEAK_COLUMNS & set(combined.columns)
    if leaked:
        raise AssertionError(f"LEAKAGE: forbidden columns present: {sorted(leaked)}")

    # --- Target sanity: accepted default_flag must be exactly {0,1}. ---
    acc_flags = set(
        combined.loc[combined["applicant_type"] == "accepted", "default_flag"]
        .dropna()
        .unique()
    )
    if not acc_flags <= {0.0, 1.0} or acc_flags != {0.0, 1.0}:
        raise AssertionError(f"default_flag among accepted not exactly {{0,1}}: {acc_flags}")

    writers.write_csv(config.PROCESSED / "processed_credit_applicants.csv", combined)
    return combined
