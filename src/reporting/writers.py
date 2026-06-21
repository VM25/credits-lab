"""Deterministic JSON and CSV writers.

All floats are rounded to config.ROUND_DP decimal places.
JSON output uses sorted keys and 2-space indent.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import config


def _round_obj(obj):
    """Recursively round floats and convert numpy scalar/array types to Python builtins."""
    if isinstance(obj, bool) or isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return round(float(obj), config.ROUND_DP)
    if isinstance(obj, np.ndarray):
        return [_round_obj(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {k: _round_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_obj(v) for v in obj]
    return obj


def write_json(path, obj):
    """Write *obj* to *path* as JSON with sorted keys, 2-space indent, floats rounded to ROUND_DP."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rounded = _round_obj(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rounded, f, sort_keys=True, indent=2)


def write_csv(path, df: pd.DataFrame):
    """Write *df* to *path* as CSV, rounding float columns to ROUND_DP decimal places."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    float_cols = df.select_dtypes(include="float").columns
    df[float_cols] = df[float_cols].round(config.ROUND_DP)
    df.to_csv(path, index=False)
