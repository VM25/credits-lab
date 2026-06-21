"""Time-aware train/val/test splitting.

Splits are by date so that thresholds and models are never tuned on future data:
earliest 70% -> train, next 15% -> val, latest 15% -> test. Ties on the date
column are resolved by stable sort, keeping original row order within a date.
"""
import numpy as np
import pandas as pd


def time_split(df: pd.DataFrame, date_col: str):
    """Return ``{"train": Index, "val": Index, "test": Index}`` of ORIGINAL index labels.

    Rows are ordered by *date_col* (ascending, stable) then sliced positionally into
    70% / 15% / 15%. The returned values are the original index labels of *df* for
    each slice, so callers can ``.loc`` them back onto the source frame.
    """
    dates = pd.to_datetime(df[date_col], errors="coerce")
    # Stable sort keeps original order for equal dates; NaT dates sink to the end.
    order = np.argsort(dates.values, kind="stable")
    ordered_index = df.index.to_numpy()[order]

    n = len(ordered_index)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)

    train_idx = ordered_index[:n_train]
    val_idx = ordered_index[n_train:n_train + n_val]
    test_idx = ordered_index[n_train + n_val:]

    return {
        "train": pd.Index(train_idx),
        "val": pd.Index(val_idx),
        "test": pd.Index(test_idx),
    }
