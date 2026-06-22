"""Isolation Forest anomaly model.

Public interface
----------------
fit(X) -> AnomalyModel
    Train on predictor matrix X (array-like or DataFrame).

AnomalyModel.score(X) -> np.ndarray
    Anomaly score in [0, 1] (higher = more anomalous).
    IsolationForest.score_samples returns higher-is-more-normal, so we
    invert and min-max normalize using the range observed at fit time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src import config


class AnomalyModel:
    """Fitted Isolation Forest wrapper that emits [0, 1] anomaly scores."""

    def __init__(
        self,
        model: IsolationForest,
        score_min: float,
        score_max: float,
    ) -> None:
        self._model = model
        # Raw score_samples range observed at fit time (higher = more normal).
        self._score_min = score_min  # most anomalous (inverted: highest anomaly)
        self._score_max = score_max  # most normal   (inverted: lowest anomaly)

    def score(self, X) -> np.ndarray:
        """Return anomaly score in [0, 1].  Higher means more anomalous."""
        if isinstance(X, pd.DataFrame):
            X = X.values
        raw = self._model.score_samples(np.asarray(X))  # higher = more normal
        # Invert: negative raw → anomalous
        inverted = -raw  # higher = more anomalous
        # Min-max normalise using fit-time range of (−raw)
        lo = -self._score_max   # smallest anomaly after inversion
        hi = -self._score_min   # largest anomaly after inversion
        denom = hi - lo
        if denom <= 0:
            return np.zeros(len(inverted))
        normalised = (inverted - lo) / denom
        return np.clip(normalised, 0.0, 1.0)


def fit(X) -> AnomalyModel:
    """Fit an IsolationForest on X and return an AnomalyModel.

    Parameters
    ----------
    X : 2-D array-like or DataFrame (train predictors only — no label columns).
    """
    if isinstance(X, pd.DataFrame):
        X = X.values
    X_arr = np.asarray(X)

    model = IsolationForest(
        random_state=config.SEED,
        contamination="auto",
    )
    model.fit(X_arr)

    raw_scores = model.score_samples(X_arr)  # higher = more normal
    score_min = float(raw_scores.min())
    score_max = float(raw_scores.max())

    return AnomalyModel(model, score_min, score_max)
