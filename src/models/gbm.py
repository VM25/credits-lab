"""Gradient-boosting classifier (challenger model).

Public interface
----------------
fit(X, y, feature_names=None) -> GBMModel
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from src import config


class GBMModel:
    """Fitted gradient-boosting model wrapper."""

    def __init__(self, clf: GradientBoostingClassifier, feature_names: list[str]) -> None:
        self._clf = clf
        self._feature_names = list(feature_names)
        importances = clf.feature_importances_
        self._feature_importances = {
            name: float(imp) for name, imp in zip(feature_names, importances)
        }

    def predict_proba(self, X) -> np.ndarray:
        """Return 1-D probability of class 1."""
        if isinstance(X, pd.DataFrame):
            X = X.values
        return self._clf.predict_proba(np.asarray(X))[:, 1]

    @property
    def feature_importances(self) -> dict[str, float]:
        """Feature name → importance score."""
        return self._feature_importances

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names


def fit(X, y, feature_names=None) -> GBMModel:
    """Fit a gradient-boosting classifier and return a GBMModel.

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

    clf = GradientBoostingClassifier(random_state=config.SEED)
    clf.fit(X_arr, y_arr)
    return GBMModel(clf, feature_names)
