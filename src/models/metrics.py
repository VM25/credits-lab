"""Thin metric helpers for the Credit & Payments Risk Decision Engine.

All functions accept array-likes (list / numpy / pandas Series).
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)

from src import config


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


# ---------------------------------------------------------------------------
# Core binary-classification metrics
# ---------------------------------------------------------------------------

def roc_auc(y, scores) -> float:
    """Area under the ROC curve."""
    return float(roc_auc_score(_arr(y), _arr(scores)))


def pr_auc(y, scores) -> float:
    """Area under the Precision-Recall curve (average precision)."""
    return float(average_precision_score(_arr(y), _arr(scores)))


def brier(y, probs) -> float:
    """Brier score loss (lower is better, in [0, 1])."""
    return float(brier_score_loss(_arr(y), _arr(probs)))


def ks(y, scores) -> float:
    """Kolmogorov–Smirnov statistic: max |TPR_cum − TNR_cum| over thresholds.

    Implemented by sorting scores and accumulating CDFs for positives and
    negatives separately.  Returns a value in [0, 1].
    """
    y_ = _arr(y)
    s_ = _arr(scores)

    # Sort descending by score
    order = np.argsort(-s_)
    y_sorted = y_[order]

    n_pos = y_.sum()
    n_neg = len(y_) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0

    cum_pos = np.cumsum(y_sorted) / n_pos          # TPR cum
    cum_neg = np.cumsum(1 - y_sorted) / n_neg      # FPR cum (negatives)
    return float(np.max(np.abs(cum_pos - cum_neg)))


def confusion_at(y, scores, threshold) -> dict:
    """Confusion matrix counts at a given score threshold.

    Positive prediction when score >= threshold.

    Returns dict with integer keys 'tp', 'fp', 'tn', 'fn'.
    """
    y_ = _arr(y).astype(int)
    pred = (_arr(scores) >= threshold).astype(int)
    tp = int(((pred == 1) & (y_ == 1)).sum())
    fp = int(((pred == 1) & (y_ == 0)).sum())
    tn = int(((pred == 0) & (y_ == 0)).sum())
    fn = int(((pred == 0) & (y_ == 1)).sum())
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def precision_recall_from_confusion(conf) -> tuple:
    """Return (precision, recall) from a confusion dict; guard zero-division → 0.0."""
    tp = conf["tp"]
    fp = conf["fp"]
    fn = conf["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return float(precision), float(recall)


# ---------------------------------------------------------------------------
# Population Stability Index
# ---------------------------------------------------------------------------

def psi(expected, actual, bins: int = 10) -> float:
    """Population Stability Index using quantile bins of `expected`.

    Guards empty bins with a small epsilon to avoid log(0).
    """
    exp_ = _arr(expected)
    act_ = _arr(actual)
    eps = 1e-8

    # Build quantile bin edges from expected distribution
    quantiles = np.linspace(0, 100, bins + 1)
    bin_edges = np.percentile(exp_, quantiles)
    # Ensure unique edges (handle flat distributions)
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0

    # Counts per bin
    exp_counts, _ = np.histogram(exp_, bins=bin_edges)
    act_counts, _ = np.histogram(act_, bins=bin_edges)

    # Proportions (guard empty bins)
    exp_pct = exp_counts / (exp_counts.sum() + eps) + eps
    act_pct = act_counts / (act_counts.sum() + eps) + eps

    psi_value = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return psi_value


def psi_status(value: float) -> str:
    """Classify PSI value using config bands.

    Returns 'stable', 'monitor', or 'material'.
    """
    if value < config.PSI_BANDS["stable"]:
        return "stable"
    if value < config.PSI_BANDS["monitor"]:
        return "monitor"
    return "material"
