"""Isotonic-regression PD calibration.

Public interface
----------------
fit(scores, y) -> Calibrator
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression

from src.models.metrics import brier as brier_score


class Calibrator:
    """Fitted isotonic calibrator."""

    def __init__(
        self,
        iso: IsotonicRegression,
        brier_before: float,
        brier_after: float,
        curve: list[dict],
    ) -> None:
        self._iso = iso
        self._brier_before = brier_before
        self._brier_after = brier_after
        self._curve = curve

    def transform(self, scores) -> np.ndarray:
        """Return calibrated probabilities clipped to [0, 1]."""
        s = np.asarray(scores, dtype=float)
        calibrated = self._iso.predict(s)
        return np.clip(calibrated, 0.0, 1.0)

    @property
    def brier_before(self) -> float:
        return self._brier_before

    @property
    def brier_after(self) -> float:
        return self._brier_after

    @property
    def curve(self) -> list[dict]:
        """Reliability curve: list of {mean_predicted, observed, count} over ~10 bins."""
        return self._curve


def _reliability_curve(calibrated: np.ndarray, y: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Build a reliability curve over quantile bins of calibrated probabilities."""
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(calibrated, quantiles)
    # Avoid duplicate edges on flat distributions
    bin_edges = np.unique(bin_edges)

    result = []
    for i in range(len(bin_edges) - 1):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        # Include right edge in last bin
        if i == len(bin_edges) - 2:
            mask = (calibrated >= lo) & (calibrated <= hi)
        else:
            mask = (calibrated >= lo) & (calibrated < hi)
        count = int(mask.sum())
        if count == 0:
            continue
        result.append({
            "mean_predicted": float(calibrated[mask].mean()),
            "observed": float(y[mask].mean()),
            "count": count,
        })
    return result


def fit(scores, y) -> Calibrator:
    """Fit an isotonic calibrator on (scores, y) and return a Calibrator.

    Parameters
    ----------
    scores : 1-D array-like of raw model scores / probabilities
    y      : 1-D array-like of binary labels
    """
    s = np.asarray(scores, dtype=float)
    y_ = np.asarray(y, dtype=float)

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(s, y_)

    calibrated = np.clip(iso.predict(s), 0.0, 1.0)

    bb = brier_score(y_, s)
    ba = brier_score(y_, calibrated)
    curve = _reliability_curve(calibrated, y_)

    return Calibrator(iso=iso, brier_before=bb, brier_after=ba, curve=curve)
