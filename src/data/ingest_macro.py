"""Download and process FRED macro series for stress overlay inputs.

Series are cached under data/raw/ so subsequent runs do not re-download.
Output: data/processed/macro_stress_inputs.csv with columns:
    date, unemployment_rate, policy_rate, inflation_rate,
    consumer_credit_delinquency_rate, credit_card_chargeoff_rate

This data is used ONLY for stress overlays / loss sensitivity (doc 02 §7) —
never to claim individual-default causality.
"""
import datetime
import io

import pandas as pd
import requests

from src import config
from src.reporting import writers

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

# Quarterly series that need forward-fill to monthly
QUARTERLY_LABELS = {"consumer_credit_delinquency_rate", "credit_card_chargeoff_rate"}

START_DATE = "2007-01-01"


def _fetch_or_load(label: str, series_id: str) -> pd.DataFrame:
    """Return a two-column DataFrame (date, label) for one FRED series.

    Uses disk cache under config.RAW; downloads only when cache is absent.
    """
    config.RAW.mkdir(parents=True, exist_ok=True)
    cache_path = config.RAW / f"fred_{series_id}.csv"

    if cache_path.exists():
        raw_text = cache_path.read_text(encoding="utf-8")
    else:
        url = FRED_BASE.format(series_id=series_id)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        raw_text = response.text
        cache_path.write_text(raw_text, encoding="utf-8")

    df = pd.read_csv(io.StringIO(raw_text))

    # Rename first column → "date" regardless of original header
    first_col = df.columns[0]
    df = df.rename(columns={first_col: "date", series_id: label})

    # Parse dates and normalise to month start
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()

    # Coerce values — FRED uses "." for missing
    df[label] = pd.to_numeric(df[label], errors="coerce")

    return df[["date", label]].drop_duplicates(subset="date").set_index("date")


def run() -> pd.DataFrame:
    """Download/cache all FRED series and produce the merged stress-input table."""
    series_frames = {}
    for label, series_id in config.FRED_SERIES.items():
        series_frames[label] = _fetch_or_load(label, series_id)

    # Build monthly date range from START_DATE to the latest available month
    latest = max(frame.index.max() for frame in series_frames.values())
    monthly_index = pd.date_range(start=START_DATE, end=latest, freq="MS")

    # Merge each series onto the monthly index
    merged = pd.DataFrame(index=monthly_index)
    merged.index.name = "date"

    for label, frame in series_frames.items():
        merged = merged.join(frame, how="left")
        if label in QUARTERLY_LABELS:
            merged[label] = merged[label].ffill()

    # Derive inflation_rate = YoY % change of CPI level, then drop helper column
    merged["inflation_rate"] = merged["inflation_cpi"].pct_change(12, fill_method=None) * 100
    merged = merged.drop(columns=["inflation_cpi"])

    # Restrict to START_DATE onward (already done by date_range, but be explicit)
    merged = merged[merged.index >= START_DATE]

    # Reset index; format date as ISO YYYY-MM-DD string
    merged = merged.reset_index()
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")

    # Reorder to the exact required column order
    output_columns = [
        "date",
        "unemployment_rate",
        "policy_rate",
        "inflation_rate",
        "consumer_credit_delinquency_rate",
        "credit_card_chargeoff_rate",
    ]
    merged = merged[output_columns]

    # Write output
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    writers.write_csv(config.PROCESSED / "macro_stress_inputs.csv", merged)

    # Record pull date
    (config.RAW / "fred_pull_date.txt").write_text(
        datetime.date.today().isoformat(), encoding="utf-8"
    )

    return merged
