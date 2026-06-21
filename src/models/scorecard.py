"""Logistic-regression scorecard (champion model).

Public interface
----------------
fit(X, y, feature_names=None) -> ScorecardModel
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config


class ScorecardModel:
    """Fitted logistic-regression scorecard wrapper."""

    def __init__(self, pipeline: Pipeline, feature_names: list[str]) -> None:
        self._pipeline = pipeline
        self._feature_names = list(feature_names)
        lr: LogisticRegression = pipeline.named_steps["lr"]
        coef = lr.coef_[0]
        self._coefficients = {name: float(c) for name, c in zip(feature_names, coef)}
        self._intercept = float(lr.intercept_[0])

    def predict_proba(self, X) -> np.ndarray:
        """Return 1-D probability of class 1."""
        if isinstance(X, pd.DataFrame):
            X = X.values
        return self._pipeline.predict_proba(np.asarray(X))[:, 1]

    @property
    def coefficients(self) -> dict[str, float]:
        """Feature name → coefficient on the standardised scale."""
        return self._coefficients

    @property
    def intercept(self) -> float:
        return self._intercept

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names


def fit(X, y, feature_names=None) -> ScorecardModel:
    """Fit a logistic-regression scorecard and return a ScorecardModel.

    Parameters
    ----------
    X : 2-D array-like or DataFrame
    y : 1-D array-like of binary labels
    feature_names : list[str] | None
        If None and X is a DataFrame, X.columns are used.
        If None and X is not a DataFrame, names default to "f0", "f1", ...
    """
    if isinstance(X, pd.DataFrame):
        if feature_names is None:
            feature_names = list(X.columns)
        X_arr = X.values
    else:
        X_arr = np.asarray(X)
        if feature_names is None:
            feature_names = [f"f{i}" for i in range(X_arr.shape[1])]

    y_arr = np.asarray(y)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, random_state=config.SEED)),
    ])
    pipeline.fit(X_arr, y_arr)
    return ScorecardModel(pipeline, feature_names)
