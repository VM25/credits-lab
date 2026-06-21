from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_OUTPUTS = ROOT / "data" / "outputs"
RNG_SEED = 20260620


CREDIT_REQUIRED_FIELDS = [
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
]

PAYMENT_REQUIRED_FIELDS = [
    "transaction_id",
    "account_id",
    "transaction_time",
    "amount",
    "merchant_category",
    "merchant_risk_band",
    "location_proxy",
    "device_proxy",
    "account_age_days",
    "transaction_count_24h",
    "amount_count_24h",
    "fraud_flag",
    "chargeback_loss",
]

STABLECOIN_REQUIRED_FIELDS = [
    "wallet_id",
    "counterparty_wallet_id",
    "transaction_time",
    "token_type",
    "amount_usd",
    "wallet_age_days",
    "inflow_24h",
    "outflow_24h",
    "transaction_count_24h",
    "counterparty_risk_score",
    "risky_address_exposure_flag",
    "stablecoin_risk_label",
]

MACRO_REQUIRED_FIELDS = [
    "date",
    "unemployment_rate",
    "policy_rate",
    "inflation_rate",
    "consumer_credit_delinquency_rate",
    "credit_card_chargeoff_rate",
]


def ensure_dirs() -> None:
    for path in [
        DATA_RAW,
        DATA_INTERIM,
        DATA_PROCESSED,
        DATA_OUTPUTS,
        ROOT / "src" / "data",
        ROOT / "src" / "models",
        ROOT / "src" / "risk",
        ROOT / "src" / "validation",
        ROOT / "src" / "reporting",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def sigmoid(values: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -35, 35)))


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def as_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): as_builtin(v) for k, v in value.items()}
    if isinstance(value, list):
        return [as_builtin(v) for v in value]
    if isinstance(value, tuple):
        return [as_builtin(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, np.ndarray):
        return as_builtin(value.tolist())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.write_text(json.dumps(as_builtin(payload), indent=2, sort_keys=False), encoding="utf-8")


def round_records(df: pd.DataFrame, decimals: int = 6) -> list[dict[str, Any]]:
    rounded = df.copy()
    for column in rounded.select_dtypes(include=[np.number]).columns:
        rounded[column] = rounded[column].round(decimals)
    return as_builtin(rounded.to_dict(orient="records"))


def date_series(start: str, periods: int, rng: np.random.Generator, max_days: int) -> pd.Series:
    offsets = np.sort(rng.integers(0, max_days, size=periods))
    return pd.to_datetime(start) + pd.to_timedelta(offsets, unit="D")


def band_counts(series: pd.Series, label: str) -> list[dict[str, Any]]:
    counts = series.value_counts(dropna=False).sort_index()
    return [{"label": str(k), "count": int(v)} for k, v in counts.items()]


def generate_credit_data(rng: np.random.Generator, n: int = 2600) -> pd.DataFrame:
    application_dates = date_series("2022-01-01", n, rng, 1460)
    credit_grades = rng.choice(["A", "B", "C", "D", "E"], size=n, p=[0.24, 0.29, 0.24, 0.15, 0.08])
    grade_numeric_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    grade_numeric = np.array([grade_numeric_map[g] for g in credit_grades])
    annual_income = np.clip(rng.lognormal(mean=11.05, sigma=0.48, size=n), 24000, 240000)
    loan_amount = np.clip(rng.lognormal(mean=9.65, sigma=0.55, size=n), 2500, 42000)
    dti_base = rng.beta(2.1, 6.0, size=n) + 0.025 * (grade_numeric - 1)
    debt_to_income = np.clip(dti_base, 0.03, 0.58)
    revolving_utilization = np.clip(rng.beta(2.0 + grade_numeric * 0.32, 5.5, size=n), 0.02, 0.98)
    delinquency_history = rng.poisson(lam=np.clip((grade_numeric - 1) * 0.18 + debt_to_income * 1.1, 0.02, 1.6))
    employment_length = np.clip(rng.normal(7.2 - 0.4 * (grade_numeric - 1), 4.2, size=n), 0, 30).round().astype(int)
    open_accounts = np.clip(rng.normal(8.5 + grade_numeric * 0.7, 3.2, size=n), 1, 28).round().astype(int)
    purpose_values = ["debt_consolidation", "home_improvement", "major_purchase", "medical", "small_business", "other"]
    loan_purpose = rng.choice(purpose_values, size=n, p=[0.46, 0.16, 0.13, 0.1, 0.07, 0.08])
    home_ownership = rng.choice(["rent", "mortgage", "own"], size=n, p=[0.43, 0.45, 0.12])
    interest_base = np.array([0.075, 0.105, 0.145, 0.205, 0.275])
    interest_rate = np.clip(interest_base[grade_numeric - 1] + rng.normal(0, 0.012, size=n), 0.045, 0.33)
    income_to_loan_ratio = annual_income / loan_amount
    debt_burden_score = np.clip(0.58 * debt_to_income + 0.32 * revolving_utilization + 0.04 * delinquency_history, 0, 1)
    loan_size_band = pd.cut(
        loan_amount,
        bins=[0, 7500, 15000, 25000, np.inf],
        labels=["small", "moderate", "large", "very_large"],
        include_lowest=True,
    ).astype(str)
    utilization_band = pd.cut(
        revolving_utilization,
        bins=[0, 0.3, 0.55, 0.75, np.inf],
        labels=["low", "moderate", "elevated", "high"],
        include_lowest=True,
    ).astype(str)
    prior_delinquency_flag = (delinquency_history > 0).astype(int)
    application_vintage = pd.PeriodIndex(application_dates, freq="Q").astype(str)
    purpose_risk = pd.Series(loan_purpose).map(
        {
            "debt_consolidation": 0.1,
            "home_improvement": -0.15,
            "major_purchase": -0.05,
            "medical": 0.15,
            "small_business": 0.35,
            "other": 0.05,
        }
    ).to_numpy()
    logit_pd = (
        -4.95
        + 0.52 * (grade_numeric - 1)
        + 2.65 * debt_to_income
        + 1.25 * revolving_utilization
        + 0.36 * delinquency_history
        - 0.10 * employment_length
        - 0.18 * np.log1p(income_to_loan_ratio)
        + 0.17 * (loan_amount > 26000)
        + purpose_risk
    )
    true_pd = np.clip(sigmoid(logit_pd), 0.004, 0.72)
    default_flag = rng.binomial(1, true_pd)
    realized_lgd = np.clip(rng.normal(0.55 + 0.04 * (grade_numeric - 3), 0.11, size=n), 0.2, 0.92)
    loss_amount_if_default = np.where(default_flag == 1, loan_amount * realized_lgd, 0.0)
    df = pd.DataFrame(
        {
            "applicant_id": [f"APP-{i:05d}" for i in range(1, n + 1)],
            "application_date": application_dates.date.astype(str),
            "loan_amount": loan_amount.round(2),
            "annual_income": annual_income.round(2),
            "debt_to_income": debt_to_income.round(4),
            "employment_length": employment_length,
            "credit_grade": credit_grades,
            "interest_rate": interest_rate.round(4),
            "loan_purpose": loan_purpose,
            "home_ownership": home_ownership,
            "delinquency_history": delinquency_history.astype(int),
            "revolving_utilization": revolving_utilization.round(4),
            "open_accounts": open_accounts,
            "default_flag": default_flag.astype(int),
            "loss_amount_if_default": loss_amount_if_default.round(2),
            "income_to_loan_ratio": income_to_loan_ratio.round(4),
            "debt_burden_score": debt_burden_score.round(4),
            "credit_utilization_band": utilization_band,
            "loan_size_band": loan_size_band,
            "credit_grade_numeric": grade_numeric,
            "prior_delinquency_flag": prior_delinquency_flag,
            "application_vintage": application_vintage,
        }
    )
    return df


def generate_payment_data(rng: np.random.Generator, n: int = 7200) -> pd.DataFrame:
    account_count = 950
    account_ids = np.array([f"ACCT-{i:05d}" for i in range(1, account_count + 1)])
    account_age_map = dict(zip(account_ids, rng.integers(3, 1850, size=account_count)))
    account_baseline_amount = dict(zip(account_ids, rng.lognormal(3.6, 0.65, size=account_count)))
    transaction_times = date_series("2024-01-01", n, rng, 730)
    transaction_times = transaction_times + pd.to_timedelta(rng.integers(0, 86400, size=n), unit="s")
    chosen_accounts = rng.choice(account_ids, size=n)
    merchant_categories = rng.choice(
        ["grocery", "travel", "electronics", "digital_goods", "fuel", "cash_like", "restaurant", "other"],
        size=n,
        p=[0.2, 0.11, 0.13, 0.12, 0.12, 0.06, 0.18, 0.08],
    )
    merchant_risk_lookup = {
        "grocery": "low",
        "fuel": "low",
        "restaurant": "low",
        "travel": "medium",
        "electronics": "medium",
        "other": "medium",
        "digital_goods": "high",
        "cash_like": "high",
    }
    merchant_risk_band = np.array([merchant_risk_lookup[c] for c in merchant_categories])
    merchant_risk_score = pd.Series(merchant_risk_band).map({"low": 0.1, "medium": 0.45, "high": 0.82}).to_numpy()
    account_age_days = np.array([account_age_map[a] for a in chosen_accounts])
    baseline_amount = np.array([account_baseline_amount[a] for a in chosen_accounts])
    amount = np.clip(rng.lognormal(np.log(baseline_amount + 12), 0.75), 2, 4500)
    new_device_flag = rng.binomial(1, np.clip(0.04 + 0.16 * merchant_risk_score + (account_age_days < 45) * 0.12, 0, 0.48))
    new_location_flag = rng.binomial(1, np.clip(0.05 + 0.12 * merchant_risk_score + (amount > 900) * 0.09, 0, 0.45))
    transaction_count_24h = rng.poisson(1.8 + 2.3 * new_device_flag + 1.7 * (merchant_risk_score > 0.7), size=n) + 1
    velocity_1h = np.maximum(0, rng.poisson(0.45 + 0.75 * new_device_flag + 0.55 * new_location_flag, size=n))
    velocity_24h = transaction_count_24h + rng.poisson(1.2, size=n)
    amount_count_24h = amount * transaction_count_24h * rng.uniform(0.75, 1.25, size=n)
    hours = pd.Series(transaction_times).dt.hour.to_numpy()
    night_transaction_flag = ((hours < 5) | (hours > 22)).astype(int)
    high_amount_flag = (amount > np.quantile(amount, 0.88)).astype(int)
    location_proxy = rng.choice(["home_region", "adjacent_region", "distant_region", "cross_border"], size=n, p=[0.68, 0.17, 0.1, 0.05])
    device_proxy = np.where(new_device_flag == 1, "new_device", rng.choice(["known_device_a", "known_device_b"], size=n))
    location_risk = pd.Series(location_proxy).map({"home_region": 0.0, "adjacent_region": 0.12, "distant_region": 0.35, "cross_border": 0.58}).to_numpy()
    amount_zscore_raw = (np.log1p(amount) - np.log1p(baseline_amount + 1)) / 0.9
    logit_fraud = (
        -6.85
        + 2.05 * merchant_risk_score
        + 1.15 * new_device_flag
        + 1.05 * new_location_flag
        + 0.75 * night_transaction_flag
        + 0.95 * high_amount_flag
        + 0.42 * velocity_1h
        + 0.46 * np.clip(amount_zscore_raw, 0, 4)
        + 1.05 * location_risk
        + (account_age_days < 30) * 1.00
    )
    fraud_probability_seed = np.clip(sigmoid(logit_fraud), 0.001, 0.65)
    fraud_flag = rng.binomial(1, fraud_probability_seed)
    chargeback_loss = np.where(fraud_flag == 1, amount * rng.uniform(0.7, 1.0, size=n), 0.0)
    df = pd.DataFrame(
        {
            "transaction_id": [f"TXN-{i:06d}" for i in range(1, n + 1)],
            "account_id": chosen_accounts,
            "transaction_time": pd.Series(transaction_times).dt.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount.round(2),
            "merchant_category": merchant_categories,
            "merchant_risk_band": merchant_risk_band,
            "location_proxy": location_proxy,
            "device_proxy": device_proxy,
            "account_age_days": account_age_days.astype(int),
            "transaction_count_24h": transaction_count_24h.astype(int),
            "amount_count_24h": amount_count_24h.round(2),
            "fraud_flag": fraud_flag.astype(int),
            "chargeback_loss": chargeback_loss.round(2),
            "velocity_1h": velocity_1h.astype(int),
            "velocity_24h": velocity_24h.astype(int),
            "merchant_risk_score": merchant_risk_score.round(4),
            "new_device_flag": new_device_flag.astype(int),
            "new_location_flag": new_location_flag.astype(int),
            "night_transaction_flag": night_transaction_flag.astype(int),
            "high_amount_flag": high_amount_flag.astype(int),
            "account_tenure_band": pd.cut(
                account_age_days,
                bins=[0, 30, 180, 720, np.inf],
                labels=["new", "seasoning", "established", "long_tenure"],
                include_lowest=True,
            ).astype(str),
        }
    )
    log_amount = np.log1p(df["amount"])
    account_mean = log_amount.groupby(df["account_id"]).transform("mean")
    account_std = log_amount.groupby(df["account_id"]).transform("std").replace(0, np.nan).fillna(log_amount.std())
    df["amount_zscore_by_account"] = ((log_amount - account_mean) / account_std).clip(-5, 5).round(4)
    return df


def generate_stablecoin_data(rng: np.random.Generator, n: int = 2200) -> pd.DataFrame:
    wallet_count = 760
    wallet_ids = np.array([f"WALLET-{i:05d}" for i in range(1, wallet_count + 1)])
    transaction_times = date_series("2024-01-01", n, rng, 730)
    transaction_times = transaction_times + pd.to_timedelta(rng.integers(0, 86400, size=n), unit="s")
    wallet_id = rng.choice(wallet_ids, size=n)
    counterparty_wallet_id = rng.choice(wallet_ids, size=n)
    same = wallet_id == counterparty_wallet_id
    counterparty_wallet_id[same] = rng.choice(wallet_ids[~np.isin(wallet_ids, wallet_id[same])], size=same.sum()) if same.sum() else counterparty_wallet_id[same]
    token_type = rng.choice(["USDC", "USDT", "DAI"], size=n, p=[0.52, 0.39, 0.09])
    amount_usd = np.clip(rng.lognormal(7.0, 1.05, size=n), 10, 350000)
    wallet_age_days = rng.integers(1, 1600, size=n)
    transaction_count_24h = rng.poisson(1.5 + (wallet_age_days < 45) * 1.1, size=n) + 1
    inflow_24h = np.clip(amount_usd * rng.uniform(0.1, 3.2, size=n) + rng.lognormal(6, 1.1, size=n), 0, 650000)
    outflow_24h = np.clip(amount_usd * rng.uniform(0.1, 3.6, size=n) + rng.lognormal(6, 1.1, size=n), 0, 650000)
    counterparty_risk_score = np.clip(rng.beta(1.3, 4.2, size=n) + rng.binomial(1, 0.045, size=n) * rng.uniform(0.35, 0.65, size=n), 0, 1)
    risky_address_exposure_flag = rng.binomial(1, np.clip(0.03 + 0.28 * counterparty_risk_score + (wallet_age_days < 30) * 0.07, 0, 0.55))
    wallet_velocity = transaction_count_24h / np.maximum(wallet_age_days / 365, 0.05)
    inflow_outflow_ratio = inflow_24h / np.maximum(outflow_24h, 1)
    counterparty_concentration = np.clip(rng.beta(1.5, 3.5, size=n) + counterparty_risk_score * 0.18, 0, 1)
    round_trip_proxy = ((inflow_outflow_ratio > 0.8) & (inflow_outflow_ratio < 1.25) & (transaction_count_24h >= 4)).astype(int)
    large_transfer_flag = (amount_usd > np.quantile(amount_usd, 0.9)).astype(int)
    new_counterparty_flag = rng.binomial(1, np.clip(0.07 + (wallet_age_days < 60) * 0.19 + counterparty_risk_score * 0.12, 0, 0.5))
    risk_exposure_raw = (
        0.34 * counterparty_risk_score
        + 0.22 * risky_address_exposure_flag
        + 0.13 * np.clip(wallet_velocity / 40, 0, 1)
        + 0.11 * counterparty_concentration
        + 0.09 * round_trip_proxy
        + 0.06 * large_transfer_flag
        + 0.05 * new_counterparty_flag
    )
    risk_exposure_score = np.clip(
        1.70 * risk_exposure_raw + 0.05 * risky_address_exposure_flag + 0.03 * large_transfer_flag,
        0,
        1,
    )
    stablecoin_risk_label = rng.binomial(1, np.clip(0.04 + 0.62 * risk_exposure_score, 0, 0.78))
    df = pd.DataFrame(
        {
            "wallet_id": wallet_id,
            "counterparty_wallet_id": counterparty_wallet_id,
            "transaction_time": pd.Series(transaction_times).dt.strftime("%Y-%m-%d %H:%M:%S"),
            "token_type": token_type,
            "amount_usd": amount_usd.round(2),
            "wallet_age_days": wallet_age_days.astype(int),
            "inflow_24h": inflow_24h.round(2),
            "outflow_24h": outflow_24h.round(2),
            "transaction_count_24h": transaction_count_24h.astype(int),
            "counterparty_risk_score": counterparty_risk_score.round(4),
            "risky_address_exposure_flag": risky_address_exposure_flag.astype(int),
            "stablecoin_risk_label": stablecoin_risk_label.astype(int),
            "wallet_velocity": wallet_velocity.round(4),
            "inflow_outflow_ratio": inflow_outflow_ratio.round(4),
            "counterparty_concentration": counterparty_concentration.round(4),
            "round_trip_proxy": round_trip_proxy.astype(int),
            "large_transfer_flag": large_transfer_flag.astype(int),
            "new_counterparty_flag": new_counterparty_flag.astype(int),
            "risk_exposure_score": risk_exposure_score.round(4),
        }
    )
    return df


def generate_macro_data(rng: np.random.Generator) -> pd.DataFrame:
    dates = pd.date_range("2022-01-01", periods=48, freq="MS")
    trend = np.linspace(0, 1, len(dates))
    unemployment = np.clip(0.036 + 0.011 * np.sin(trend * math.pi * 2) + rng.normal(0, 0.002, len(dates)), 0.03, 0.07)
    policy_rate = np.clip(0.012 + trend * 0.035 + rng.normal(0, 0.002, len(dates)), 0.005, 0.065)
    inflation = np.clip(0.025 + 0.019 * np.sin(trend * math.pi * 1.5 + 0.5) + rng.normal(0, 0.003, len(dates)), 0.015, 0.075)
    consumer_dq = np.clip(0.021 + 0.55 * unemployment + rng.normal(0, 0.002, len(dates)), 0.025, 0.075)
    card_chargeoff = np.clip(0.018 + 0.45 * consumer_dq + rng.normal(0, 0.002, len(dates)), 0.015, 0.06)
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "unemployment_rate": unemployment.round(4),
            "policy_rate": policy_rate.round(4),
            "inflation_rate": inflation.round(4),
            "consumer_credit_delinquency_rate": consumer_dq.round(4),
            "credit_card_chargeoff_rate": card_chargeoff.round(4),
        }
    )


def time_split(df: pd.DataFrame, date_col: str) -> tuple[pd.Index, pd.Index, pd.Index]:
    ordered = df.sort_values(date_col).index.to_numpy()
    n = len(ordered)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    return pd.Index(ordered[:train_end]), pd.Index(ordered[train_end:val_end]), pd.Index(ordered[val_end:])


@dataclass
class FeatureSpec:
    numeric: list[str]
    categorical: list[str]
    means: dict[str, float]
    stds: dict[str, float]
    categories: dict[str, list[str]]
    feature_names: list[str]


def fit_feature_spec(df: pd.DataFrame, numeric: list[str], categorical: list[str]) -> FeatureSpec:
    means = {column: float(df[column].mean()) for column in numeric}
    stds = {column: float(df[column].std(ddof=0) or 1.0) for column in numeric}
    categories = {column: sorted(df[column].astype(str).dropna().unique().tolist()) for column in categorical}
    feature_names = numeric.copy()
    for column in categorical:
        feature_names.extend([f"{column}={category}" for category in categories[column]])
    return FeatureSpec(numeric, categorical, means, stds, categories, feature_names)


def transform_features(df: pd.DataFrame, spec: FeatureSpec) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    numeric_frame = pd.DataFrame(index=df.index)
    for column in spec.numeric:
        numeric_frame[column] = (df[column].astype(float) - spec.means[column]) / spec.stds[column]
    parts.append(numeric_frame)
    for column in spec.categorical:
        cat = pd.Categorical(df[column].astype(str), categories=spec.categories[column])
        dummies = pd.get_dummies(cat, prefix=column, prefix_sep="=", dtype=float)
        expected = [f"{column}={category}" for category in spec.categories[column]]
        dummies = dummies.reindex(columns=expected, fill_value=0.0)
        dummies.index = df.index
        parts.append(dummies)
    frame = pd.concat(parts, axis=1)
    return frame.reindex(columns=spec.feature_names, fill_value=0.0)


@dataclass
class LogisticModel:
    intercept: float
    weights: np.ndarray
    feature_names: list[str]

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return np.asarray(sigmoid(self.intercept + x @ self.weights), dtype=float)

    def coefficient_table(self) -> pd.DataFrame:
        return pd.DataFrame({"feature": self.feature_names, "coefficient": self.weights}).sort_values("coefficient", ascending=False)


def fit_logistic_model(x: np.ndarray, y: np.ndarray, feature_names: list[str], l2: float = 0.05) -> LogisticModel:
    y_mean = np.clip(y.mean(), 1e-4, 1 - 1e-4)
    initial = np.zeros(x.shape[1] + 1)
    initial[0] = math.log(y_mean / (1 - y_mean))

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        z = theta[0] + x @ theta[1:]
        p = np.clip(sigmoid(z), 1e-6, 1 - 1e-6)
        loss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)) + l2 * np.sum(theta[1:] ** 2) / (2 * len(y))
        grad = np.empty_like(theta)
        error = p - y
        grad[0] = np.mean(error)
        grad[1:] = (x.T @ error) / len(y) + l2 * theta[1:] / len(y)
        return float(loss), grad

    result = minimize(lambda t: objective(t), initial, jac=True, method="L-BFGS-B", options={"maxiter": 500})
    if not result.success:
        raise RuntimeError(f"Logistic model failed to converge: {result.message}")
    return LogisticModel(float(result.x[0]), result.x[1:].astype(float), feature_names)


@dataclass
class DecisionStump:
    feature_index: int
    threshold: float
    left_value: float
    right_value: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.where(x[:, self.feature_index] <= self.threshold, self.left_value, self.right_value)


@dataclass
class SimpleGradientBoostingClassifier:
    feature_names: list[str]
    n_estimators: int = 90
    learning_rate: float = 0.08
    max_bins: int = 12
    base_log_odds: float = 0.0
    stumps: list[DecisionStump] | None = None
    feature_importance_: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> "SimpleGradientBoostingClassifier":
        y_mean = np.clip(y.mean(), 1e-4, 1 - 1e-4)
        self.base_log_odds = math.log(y_mean / (1 - y_mean))
        scores = np.full(len(y), self.base_log_odds)
        self.stumps = []
        self.feature_importance_ = np.zeros(x.shape[1], dtype=float)
        for _ in range(self.n_estimators):
            probabilities = np.asarray(sigmoid(scores), dtype=float)
            residual = y - probabilities
            stump, gain = self._fit_stump(x, residual)
            scores += self.learning_rate * stump.predict(x)
            self.stumps.append(stump)
            self.feature_importance_[stump.feature_index] += max(gain, 0.0)
        total_importance = self.feature_importance_.sum()
        if total_importance > 0:
            self.feature_importance_ = self.feature_importance_ / total_importance
        return self

    def _fit_stump(self, x: np.ndarray, residual: np.ndarray) -> tuple[DecisionStump, float]:
        base_sse = float(np.sum((residual - residual.mean()) ** 2))
        best: DecisionStump | None = None
        best_sse = float("inf")
        for j in range(x.shape[1]):
            values = x[:, j]
            quantiles = np.unique(np.quantile(values, np.linspace(0.08, 0.92, self.max_bins)))
            for threshold in quantiles:
                left = values <= threshold
                right = ~left
                if left.sum() < 20 or right.sum() < 20:
                    continue
                left_value = float(residual[left].mean())
                right_value = float(residual[right].mean())
                sse = float(np.sum((residual[left] - left_value) ** 2) + np.sum((residual[right] - right_value) ** 2))
                if sse < best_sse:
                    best_sse = sse
                    best = DecisionStump(j, float(threshold), left_value, right_value)
        if best is None:
            best = DecisionStump(0, float(np.median(x[:, 0])), float(residual.mean()), float(residual.mean()))
            best_sse = base_sse
        return best, base_sse - best_sse

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.stumps is None:
            raise RuntimeError("Gradient boosting model has not been fit.")
        scores = np.full(x.shape[0], self.base_log_odds)
        for stump in self.stumps:
            scores += self.learning_rate * stump.predict(x)
        return np.asarray(sigmoid(scores), dtype=float)

    def feature_importance_table(self) -> pd.DataFrame:
        if self.feature_importance_ is None:
            raise RuntimeError("Gradient boosting model has not been fit.")
        return pd.DataFrame({"feature": self.feature_names, "importance": self.feature_importance_}).sort_values("importance", ascending=False)


@dataclass
class QuantileCalibrator:
    edges: list[float]
    values: list[float]
    fallback: float

    def predict(self, scores: np.ndarray) -> np.ndarray:
        if len(self.edges) <= 2:
            return np.full_like(scores, self.fallback, dtype=float)
        bins = np.searchsorted(np.array(self.edges[1:-1]), scores, side="right")
        values = np.array(self.values)
        bins = np.clip(bins, 0, len(values) - 1)
        return values[bins]


def fit_quantile_calibrator(scores: np.ndarray, y: np.ndarray, bins: int = 10) -> QuantileCalibrator:
    scores = np.asarray(scores, dtype=float)
    y = np.asarray(y, dtype=float)
    fallback = float(np.clip(y.mean(), 1e-5, 1 - 1e-5))
    edges = np.unique(np.quantile(scores, np.linspace(0, 1, bins + 1))).tolist()
    if len(edges) <= 2:
        return QuantileCalibrator(edges=[0.0, 1.0], values=[fallback], fallback=fallback)
    values: list[float] = []
    alpha = 20.0
    for i in range(len(edges) - 1):
        if i == len(edges) - 2:
            mask = (scores >= edges[i]) & (scores <= edges[i + 1])
        else:
            mask = (scores >= edges[i]) & (scores < edges[i + 1])
        count = int(mask.sum())
        observed = float(y[mask].sum()) if count else 0.0
        smoothed = (observed + alpha * fallback) / (count + alpha)
        values.append(float(np.clip(smoothed, 0.0001, 0.9999)))
    values = np.maximum.accumulate(values).tolist()
    return QuantileCalibrator(edges=edges, values=values, fallback=fallback)


def roc_auc_score(y: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    scores = np.asarray(scores)
    if y.sum() == 0 or y.sum() == len(y):
        return float("nan")
    order = np.argsort(-scores)
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    tpr = np.r_[0, tp / tp[-1]]
    fpr = np.r_[0, fp / fp[-1]]
    return float(np.trapezoid(tpr, fpr))


def pr_auc_score(y: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    scores = np.asarray(scores)
    if y.sum() == 0:
        return float("nan")
    order = np.argsort(-scores)
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    recall = tp / tp[-1]
    precision = tp / np.maximum(tp + fp, 1)
    recall = np.r_[0, recall]
    precision = np.r_[precision[0], precision]
    return float(np.trapezoid(precision, recall))


def brier_score(y: np.ndarray, probabilities: np.ndarray) -> float:
    return float(np.mean((np.asarray(probabilities) - np.asarray(y)) ** 2))


def ks_statistic(y: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    if y.sum() == 0 or y.sum() == len(y):
        return float("nan")
    order = np.argsort(-scores)
    y_sorted = y[order]
    tp = np.cumsum(y_sorted) / y.sum()
    fp = np.cumsum(1 - y_sorted) / (len(y) - y.sum())
    return float(np.max(np.abs(tp - fp)))


def confusion_at_threshold(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, int]:
    predictions = (scores >= threshold).astype(int)
    y = y.astype(int)
    return {
        "true_positive": int(((predictions == 1) & (y == 1)).sum()),
        "false_positive": int(((predictions == 1) & (y == 0)).sum()),
        "true_negative": int(((predictions == 0) & (y == 0)).sum()),
        "false_negative": int(((predictions == 0) & (y == 1)).sum()),
    }


def precision_recall_from_confusion(confusion: dict[str, int]) -> tuple[float, float]:
    tp = confusion["true_positive"]
    fp = confusion["false_positive"]
    fn = confusion["false_negative"]
    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    return precision, recall


def calibration_table(scores: np.ndarray, y: np.ndarray, bins: int = 10) -> pd.DataFrame:
    frame = pd.DataFrame({"score": scores, "target": y})
    frame["bin"] = pd.qcut(frame["score"].rank(method="first"), q=bins, labels=False, duplicates="drop") + 1
    grouped = frame.groupby("bin", as_index=False).agg(
        applicant_count=("target", "size"),
        average_predicted_pd=("score", "mean"),
        actual_default_rate=("target", "mean"),
        defaults=("target", "sum"),
    )
    grouped["calibration_gap"] = grouped["average_predicted_pd"] - grouped["actual_default_rate"]
    return grouped


def population_stability_index(expected_scores: np.ndarray, actual_scores: np.ndarray, bins: int = 10) -> float:
    edges = np.unique(np.quantile(expected_scores, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    expected_counts = np.histogram(expected_scores, bins=edges)[0] / len(expected_scores)
    actual_counts = np.histogram(actual_scores, bins=edges)[0] / len(actual_scores)
    expected_counts = np.clip(expected_counts, 1e-5, None)
    actual_counts = np.clip(actual_counts, 1e-5, None)
    return float(np.sum((actual_counts - expected_counts) * np.log(actual_counts / expected_counts)))


def psi_status(psi: float) -> str:
    if psi < 0.10:
        return "stable"
    if psi < 0.25:
        return "monitor"
    return "material shift"


def quality_row(
    dataset_name: str,
    df: pd.DataFrame,
    id_column: str | None,
    target_column: str | None,
    date_column: str | None,
    required_fields: list[str],
    leakage_status: str,
) -> dict[str, Any]:
    missing_required = [field for field in required_fields if field not in df.columns]
    schema_status = "Pass" if not missing_required else f"Fail: missing {', '.join(missing_required)}"
    duplicate_count = int(df[id_column].duplicated().sum()) if id_column else 0
    target_rate = float(df[target_column].mean()) if target_column and target_column in df.columns else np.nan
    date_min = str(pd.to_datetime(df[date_column]).min().date()) if date_column else ""
    date_max = str(pd.to_datetime(df[date_column]).max().date()) if date_column else ""
    return {
        "dataset_name": dataset_name,
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "missing_value_count": int(df.isna().sum().sum()),
        "duplicate_id_count": duplicate_count,
        "target_rate": round(target_rate, 6) if not np.isnan(target_rate) else "",
        "date_min": date_min,
        "date_max": date_max,
        "leakage_check_status": leakage_status,
        "schema_check_status": schema_status,
    }


def build_data_layer() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(RNG_SEED)
    credit = generate_credit_data(rng)
    payments = generate_payment_data(rng)
    stablecoin = generate_stablecoin_data(rng)
    macro = generate_macro_data(rng)

    credit.to_csv(DATA_RAW / "credit_applicants_synthetic.csv", index=False)
    payments.to_csv(DATA_RAW / "payment_transactions_synthetic.csv", index=False)
    stablecoin.to_csv(DATA_RAW / "stablecoin_transactions_synthetic.csv", index=False)
    macro.to_csv(DATA_RAW / "macro_stress_inputs_synthetic.csv", index=False)

    credit.to_csv(DATA_PROCESSED / "processed_credit_applicants.csv", index=False)
    credit.to_csv(DATA_PROCESSED / "underwriting_model_dataset.csv", index=False)
    payments.to_csv(DATA_PROCESSED / "processed_payment_transactions.csv", index=False)
    payments.to_csv(DATA_PROCESSED / "fraud_model_dataset.csv", index=False)
    stablecoin.to_csv(DATA_PROCESSED / "processed_stablecoin_transactions.csv", index=False)
    macro.to_csv(DATA_PROCESSED / "macro_stress_inputs.csv", index=False)

    validation_dataset = pd.concat(
        [
            credit.assign(validation_domain="credit")[["validation_domain", "applicant_id", "application_date", "default_flag"]],
            payments.assign(validation_domain="payments")[["validation_domain", "transaction_id", "transaction_time", "fraud_flag"]].rename(
                columns={"transaction_id": "applicant_id", "transaction_time": "application_date", "fraud_flag": "default_flag"}
            ),
        ],
        ignore_index=True,
    )
    validation_dataset.to_csv(DATA_PROCESSED / "validation_dataset.csv", index=False)

    quality = pd.DataFrame(
        [
            quality_row(
                "processed_credit_applicants",
                credit,
                "applicant_id",
                "default_flag",
                "application_date",
                CREDIT_REQUIRED_FIELDS,
                "Pass: post-origination outcome fields excluded from model features",
            ),
            quality_row(
                "processed_payment_transactions",
                payments,
                "transaction_id",
                "fraud_flag",
                "transaction_time",
                PAYMENT_REQUIRED_FIELDS,
                "Pass: chargeback outcome excluded from scoring features",
            ),
            quality_row(
                "processed_stablecoin_transactions",
                stablecoin,
                None,
                "stablecoin_risk_label",
                "transaction_time",
                STABLECOIN_REQUIRED_FIELDS,
                "Pass: future wallet labels excluded from scoring features",
            ),
            quality_row(
                "macro_stress_inputs",
                macro,
                None,
                None,
                "date",
                MACRO_REQUIRED_FIELDS,
                "Pass: macro variables used only for stress assumptions",
            ),
        ]
    )
    if quality["leakage_check_status"].str.startswith("Fail").any() or quality["schema_check_status"].str.startswith("Fail").any():
        quality.to_csv(DATA_OUTPUTS / "data_quality_report.csv", index=False)
        raise RuntimeError("Data quality gate failed.")
    quality.to_csv(DATA_OUTPUTS / "data_quality_report.csv", index=False)
    return {"credit": credit, "payments": payments, "stablecoin": stablecoin, "macro": macro, "quality": quality}


def risk_grade_from_pd(pd_value: float) -> str:
    if pd_value < 0.02:
        return "A"
    if pd_value < 0.05:
        return "B"
    if pd_value < 0.10:
        return "C"
    if pd_value < 0.20:
        return "D"
    return "E"


def decision_from_pd(pd_value: float, approve_cutoff: float = 0.06, decline_cutoff: float = 0.12) -> str:
    if pd_value < approve_cutoff:
        return "Approve"
    if pd_value < decline_cutoff:
        return "Review"
    return "Decline"


def lgd_assumption(risk_grade: str) -> float:
    if risk_grade in {"A", "B"}:
        return 0.35
    if risk_grade in {"C", "D"}:
        return 0.55
    return 0.75


def recommended_credit_limit(row: pd.Series) -> float:
    if row["decision"] == "Decline":
        return 0.0
    grade_factor = {"A": 0.24, "B": 0.20, "C": 0.16, "D": 0.10, "E": 0.06}[row["risk_grade"]]
    affordability = np.clip((1 - row["debt_to_income"]) * row["income_to_loan_ratio"] / 4.5, 0.35, 1.25)
    review_factor = 0.72 if row["decision"] == "Review" else 1.0
    limit_value = min(row["loan_amount"] * 1.15, row["annual_income"] * grade_factor * affordability * review_factor)
    return float(max(500.0, round(limit_value / 100) * 100))


def applicant_reason_codes(row: pd.Series) -> list[str]:
    reasons: list[tuple[float, str]] = []
    reasons.append((row["debt_to_income"], "high debt-to-income"))
    reasons.append((-row["income_to_loan_ratio"], "low income-to-loan coverage"))
    reasons.append((row["revolving_utilization"], "high revolving utilization"))
    reasons.append((float(row["prior_delinquency_flag"]), "prior delinquency"))
    reasons.append((row["credit_grade_numeric"] / 5.0, "weak credit grade"))
    reasons.append((row["loan_amount"] / 42000.0, "large loan amount"))
    reasons.append((row["PD"], "high predicted default risk"))
    selected = [label for _, label in sorted(reasons, key=lambda item: item[0], reverse=True)[:3]]
    if row["decision"] == "Approve" and row["PD"] < 0.035:
        selected[0] = "modeled PD below approve cutoff"
    return selected


def summarize_distribution(values: pd.Series, bins: list[float], labels: list[str]) -> list[dict[str, Any]]:
    categories = pd.cut(values, bins=bins, labels=labels, include_lowest=True)
    return [{"label": str(label), "count": int((categories == label).sum())} for label in labels]


def build_underwriting_engine(credit: pd.DataFrame) -> dict[str, Any]:
    working = credit.copy()
    train_idx, val_idx, test_idx = time_split(working, "application_date")
    numeric = [
        "loan_amount",
        "annual_income",
        "debt_to_income",
        "employment_length",
        "interest_rate",
        "delinquency_history",
        "revolving_utilization",
        "open_accounts",
        "income_to_loan_ratio",
        "debt_burden_score",
        "credit_grade_numeric",
        "prior_delinquency_flag",
    ]
    categorical = ["credit_grade", "loan_purpose", "home_ownership", "credit_utilization_band", "loan_size_band"]
    spec = fit_feature_spec(working.loc[train_idx], numeric, categorical)
    x_train = transform_features(working.loc[train_idx], spec).to_numpy(float)
    x_val = transform_features(working.loc[val_idx], spec).to_numpy(float)
    x_test = transform_features(working.loc[test_idx], spec).to_numpy(float)
    x_all = transform_features(working, spec).to_numpy(float)
    y_train = working.loc[train_idx, "default_flag"].to_numpy(int)
    y_val = working.loc[val_idx, "default_flag"].to_numpy(int)
    y_test = working.loc[test_idx, "default_flag"].to_numpy(int)

    champion = fit_logistic_model(x_train, y_train, spec.feature_names, l2=0.2)
    champion_val_raw = champion.predict_proba(x_val)
    champion_calibrator = fit_quantile_calibrator(champion_val_raw, y_val, bins=10)
    champion_all_raw = champion.predict_proba(x_all)
    champion_pd = champion_calibrator.predict(champion_all_raw)
    champion_test_pd = champion_calibrator.predict(champion.predict_proba(x_test))
    champion_train_pd = champion_calibrator.predict(champion.predict_proba(x_train))

    challenger = SimpleGradientBoostingClassifier(spec.feature_names).fit(x_train, y_train)
    challenger_val_raw = challenger.predict_proba(x_val)
    challenger_calibrator = fit_quantile_calibrator(challenger_val_raw, y_val, bins=10)
    challenger_test_pd = challenger_calibrator.predict(challenger.predict_proba(x_test))
    challenger_all_pd = challenger_calibrator.predict(challenger.predict_proba(x_all))

    decisions = working.copy()
    decisions["PD"] = np.clip(champion_pd, 0.0001, 0.9999)
    decisions["challenger_PD"] = np.clip(challenger_all_pd, 0.0001, 0.9999)
    decisions["risk_grade"] = decisions["PD"].map(risk_grade_from_pd)
    decisions["decision"] = decisions["PD"].map(decision_from_pd)
    decisions["recommended_credit_limit"] = decisions.apply(recommended_credit_limit, axis=1).round(2)
    decisions["LGD"] = decisions["risk_grade"].map(lgd_assumption)
    decisions["EAD"] = np.where(decisions["decision"] == "Decline", 0.0, decisions["loan_amount"])
    decisions["expected_loss"] = (decisions["PD"] * decisions["LGD"] * decisions["EAD"]).round(2)
    decisions["expected_loss_rate"] = np.where(decisions["EAD"] > 0, decisions["expected_loss"] / decisions["EAD"], 0.0)
    decisions["model_used"] = "champion_logistic_scorecard_calibrated"
    reason_codes = decisions.apply(applicant_reason_codes, axis=1)
    decisions["top_reason_1"] = [codes[0] for codes in reason_codes]
    decisions["top_reason_2"] = [codes[1] for codes in reason_codes]
    decisions["top_reason_3"] = [codes[2] for codes in reason_codes]

    output_columns = [
        "applicant_id",
        "PD",
        "risk_grade",
        "decision",
        "recommended_credit_limit",
        "LGD",
        "EAD",
        "expected_loss",
        "top_reason_1",
        "top_reason_2",
        "top_reason_3",
        "model_used",
        "loan_amount",
        "annual_income",
        "debt_to_income",
        "credit_grade",
        "loan_purpose",
        "application_vintage",
        "default_flag",
        "interest_rate",
        "expected_loss_rate",
        "challenger_PD",
    ]
    decisions[output_columns].to_csv(DATA_OUTPUTS / "underwriting_decisions.csv", index=False)

    decision_summary = decisions.groupby("decision", as_index=False).agg(
        applicant_count=("applicant_id", "count"),
        average_PD=("PD", "mean"),
        expected_loss=("expected_loss", "sum"),
        exposure=("EAD", "sum"),
        observed_default_rate=("default_flag", "mean"),
    )
    decision_summary["applicant_share"] = decision_summary["applicant_count"] / len(decisions)
    grade_summary = decisions.groupby("risk_grade", as_index=False).agg(
        applicant_count=("applicant_id", "count"),
        average_PD=("PD", "mean"),
        observed_default_rate=("default_flag", "mean"),
        expected_loss=("expected_loss", "sum"),
        exposure=("EAD", "sum"),
    )
    grade_summary["expected_loss_rate"] = grade_summary["expected_loss"] / grade_summary["exposure"].replace(0, np.nan)
    grade_summary["expected_loss_rate"] = grade_summary["expected_loss_rate"].fillna(0)
    reason_frequency = (
        pd.concat([decisions["top_reason_1"], decisions["top_reason_2"], decisions["top_reason_3"]])
        .value_counts()
        .rename_axis("reason_code")
        .reset_index(name="count")
    )
    approval_loss_curve = []
    for cutoff in np.linspace(0.03, 0.12, 10):
        approved = decisions["PD"] < cutoff
        exposure = float(decisions.loc[approved, "loan_amount"].sum())
        loss = float((decisions.loc[approved, "PD"] * decisions.loc[approved, "LGD"] * decisions.loc[approved, "loan_amount"]).sum())
        approval_loss_curve.append(
            {
                "approval_pd_cutoff": round(float(cutoff), 4),
                "approval_rate": safe_divide(float(approved.sum()), len(decisions)),
                "expected_loss": loss,
                "loss_rate": safe_divide(loss, exposure),
            }
        )
    champion_comparison = pd.DataFrame(
        {
            "applicant_id": decisions["applicant_id"],
            "champion_PD": decisions["PD"],
            "challenger_PD": decisions["challenger_PD"],
            "default_flag": decisions["default_flag"],
        }
    )

    credit_validation = {
        "train_idx": train_idx,
        "val_idx": val_idx,
        "test_idx": test_idx,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "champion_train_pd": champion_train_pd,
        "champion_test_pd": champion_test_pd,
        "challenger_test_pd": challenger_test_pd,
        "champion": champion,
        "challenger": challenger,
        "feature_spec": spec,
        "calibration_table": calibration_table(champion_test_pd, y_test, 10),
        "champion_coefficients": champion.coefficient_table(),
        "challenger_importance": challenger.feature_importance_table(),
        "champion_comparison": champion_comparison,
    }
    calibration = credit_validation["calibration_table"]
    calibration.to_csv(DATA_OUTPUTS / "decile_default_table.csv", index=False)
    write_json(
        DATA_OUTPUTS / "calibration_curve.json",
        {
            "model_name": "champion_logistic_scorecard",
            "points": round_records(
                calibration.rename(
                    columns={
                        "average_predicted_pd": "predicted_probability",
                        "actual_default_rate": "observed_default_rate",
                    }
                )
            ),
        },
    )
    underwriting_policy_summary = {
        "approval_mix": round_records(decision_summary),
        "risk_grade_mix": round_records(grade_summary),
        "average_PD_by_decision": round_records(decision_summary[["decision", "average_PD"]]),
        "expected_loss_by_decision": round_records(decision_summary[["decision", "expected_loss", "exposure"]]),
        "top_decline_reasons": round_records(reason_frequency.head(10)),
        "charts": {
            "PD_distribution": summarize_distribution(
                decisions["PD"],
                [0, 0.02, 0.05, 0.10, 0.20, 1],
                ["<2%", "2%-5%", "5%-10%", "10%-20%", "20%+"],
            ),
            "risk_grade_distribution": band_counts(decisions["risk_grade"], "risk_grade"),
            "approval_review_decline_mix": round_records(decision_summary[["decision", "applicant_count", "applicant_share"]]),
            "approval_rate_vs_expected_loss": approval_loss_curve,
            "default_rate_by_risk_grade": round_records(grade_summary[["risk_grade", "observed_default_rate", "average_PD"]]),
            "expected_loss_by_risk_grade": round_records(grade_summary[["risk_grade", "expected_loss", "expected_loss_rate", "exposure"]]),
            "top_reason_code_frequency": round_records(reason_frequency),
            "champion_vs_challenger_PD_comparison": round_records(champion_comparison.sample(80, random_state=7)),
        },
        "policy_assumptions": {
            "approve_pd_cutoff": 0.06,
            "decline_pd_cutoff": 0.12,
            "risk_grade_bands": {"A": "<2%", "B": "2%-5%", "C": "5%-10%", "D": "10%-20%", "E": "20%+"},
            "LGD_assumption": "35% for A-B, 55% for C-D, 75% for E based on documented project assumptions",
            "EAD_assumption": "installment-style EAD equals loan_amount; declined applicants receive zero approved exposure",
        },
    }
    write_json(DATA_OUTPUTS / "underwriting_policy_summary.json", underwriting_policy_summary)
    write_json(
        DATA_OUTPUTS / "underwriting_decisions.json",
        {
            "metadata": {
                "source": "data/outputs/underwriting_decisions.csv",
                "model_used": "champion_logistic_scorecard_calibrated",
                "synthetic_data_disclosure": "Applicant data and labels are synthetic for portfolio demonstration.",
            },
            "records": round_records(decisions[output_columns].sort_values("PD", ascending=False).head(500)),
            "charts": underwriting_policy_summary["charts"],
        },
    )
    return {
        "decisions": decisions,
        "validation": credit_validation,
        "summary": underwriting_policy_summary,
    }


def robust_scaled(series: pd.Series) -> pd.Series:
    median = series.median()
    mad = (series - median).abs().median()
    if mad == 0:
        mad = series.std() or 1.0
    return ((series - median) / (1.4826 * mad)).clip(-6, 6)


def payment_action_from_score(score: float) -> str:
    if score < 0.35:
        return "Approve"
    if score < 0.60:
        return "Step-up verification"
    if score < 0.80:
        return "Manual review"
    return "Block"


def transaction_reason_codes(row: pd.Series) -> list[str]:
    candidates = [
        (row["amount"] / 4500.0, "high amount"),
        (row["velocity_24h"] / 14.0, "high velocity"),
        (float(row["new_device_flag"]), "new device"),
        (float(row["new_location_flag"]), "new location"),
        (row["merchant_risk_score"], "high-risk merchant"),
        (1.0 if row["account_age_days"] < 45 else 0.0, "short account age"),
        (max(row["amount_zscore_by_account"], 0) / 5.0, "unusual account amount"),
    ]
    return [label for _, label in sorted(candidates, key=lambda item: item[0], reverse=True)[:3]]


def threshold_tradeoff(
    y: np.ndarray,
    scores: np.ndarray,
    amount: np.ndarray,
    thresholds: np.ndarray,
    loss_probability: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    loss_probability = scores if loss_probability is None else loss_probability
    rows = []
    for threshold in thresholds:
        flagged = scores >= threshold
        fp = int(((flagged == 1) & (y == 0)).sum())
        tp = int(((flagged == 1) & (y == 1)).sum())
        fn = int(((flagged == 0) & (y == 1)).sum())
        rows.append(
            {
                "threshold": round(float(threshold), 4),
                "fraud_captured": safe_divide(tp, int(y.sum())),
                "false_positives": fp,
                "false_positive_rate": safe_divide(fp, int((y == 0).sum())),
                "false_negatives": fn,
                "manual_review_volume": int(flagged.sum()),
                "expected_fraud_loss": float((loss_probability[~flagged] * amount[~flagged] * 0.90).sum()),
            }
        )
    return rows


def build_fraud_engine(payments: pd.DataFrame) -> dict[str, Any]:
    working = payments.copy()
    train_idx, val_idx, test_idx = time_split(working, "transaction_time")
    numeric = [
        "amount",
        "account_age_days",
        "transaction_count_24h",
        "amount_count_24h",
        "velocity_1h",
        "velocity_24h",
        "amount_zscore_by_account",
        "merchant_risk_score",
        "new_device_flag",
        "new_location_flag",
        "night_transaction_flag",
        "high_amount_flag",
    ]
    categorical = ["merchant_category", "merchant_risk_band", "location_proxy", "device_proxy", "account_tenure_band"]
    spec = fit_feature_spec(working.loc[train_idx], numeric, categorical)
    x_train = transform_features(working.loc[train_idx], spec).to_numpy(float)
    x_val = transform_features(working.loc[val_idx], spec).to_numpy(float)
    x_test = transform_features(working.loc[test_idx], spec).to_numpy(float)
    x_all = transform_features(working, spec).to_numpy(float)
    y_train = working.loc[train_idx, "fraud_flag"].to_numpy(int)
    y_val = working.loc[val_idx, "fraud_flag"].to_numpy(int)
    y_test = working.loc[test_idx, "fraud_flag"].to_numpy(int)
    supervised = fit_logistic_model(x_train, y_train, spec.feature_names, l2=0.1)
    raw_val = supervised.predict_proba(x_val)
    calibrator = fit_quantile_calibrator(raw_val, y_val, bins=8)
    fraud_probability = np.clip(supervised.predict_proba(x_all), 0.0005, 0.95)
    fraud_test_probability = np.clip(supervised.predict_proba(x_test), 0.0005, 0.95)
    fraud_test_calibrated = calibrator.predict(supervised.predict_proba(x_test))

    rules_score = np.clip(
        0.18 * working["high_amount_flag"]
        + 0.18 * np.clip(working["velocity_24h"] / 10, 0, 1)
        + 0.15 * working["new_device_flag"]
        + 0.13 * working["new_location_flag"]
        + 0.16 * working["merchant_risk_score"]
        + 0.10 * (working["account_age_days"] < 45).astype(float)
        + 0.10 * np.clip(working["amount_zscore_by_account"].clip(lower=0) / 4, 0, 1),
        0,
        1,
    )
    anomaly_score = np.clip(
        0.35 * np.clip(robust_scaled(np.log1p(working["amount"])).clip(lower=0) / 5, 0, 1)
        + 0.25 * np.clip(robust_scaled(working["velocity_24h"]).clip(lower=0) / 5, 0, 1)
        + 0.15 * working["new_device_flag"]
        + 0.12 * working["new_location_flag"]
        + 0.13 * working["merchant_risk_score"],
        0,
        1,
    )
    supervised_rank_score = pd.Series(fraud_probability, index=working.index).rank(pct=True).to_numpy()
    fraud_score = np.clip(0.58 * supervised_rank_score + 0.24 * rules_score + 0.18 * anomaly_score, 0, 1)
    alerts = working.copy()
    alerts["fraud_probability"] = fraud_probability
    alerts["fraud_score"] = fraud_score
    alerts["anomaly_score"] = anomaly_score
    alerts["payment_action"] = alerts["fraud_score"].map(payment_action_from_score)
    alerts["loss_severity"] = 0.90
    alerts["expected_fraud_loss"] = alerts["fraud_probability"] * alerts["amount"] * alerts["loss_severity"]
    reason_codes = alerts.apply(transaction_reason_codes, axis=1)
    alerts["top_reason_1"] = [codes[0] for codes in reason_codes]
    alerts["top_reason_2"] = [codes[1] for codes in reason_codes]
    alerts["top_reason_3"] = [codes[2] for codes in reason_codes]
    review_candidates = alerts[alerts["payment_action"].isin(["Manual review", "Step-up verification"])].copy()
    review_candidates["priority_score"] = review_candidates["fraud_score"] * np.log1p(review_candidates["amount"]) + review_candidates["expected_fraud_loss"] / 250
    review_candidates = review_candidates.sort_values("priority_score", ascending=False)
    review_capacity = 140
    priority_map = {idx: rank + 1 for rank, idx in enumerate(review_candidates.head(review_capacity).index)}
    alerts["manual_review_priority"] = alerts.index.map(priority_map).fillna(0).astype(int)

    output_columns = [
        "transaction_id",
        "account_id",
        "transaction_time",
        "amount",
        "fraud_probability",
        "fraud_score",
        "anomaly_score",
        "payment_action",
        "expected_fraud_loss",
        "top_reason_1",
        "top_reason_2",
        "top_reason_3",
        "manual_review_priority",
        "merchant_risk_band",
        "fraud_flag",
    ]
    alerts[output_columns].to_csv(DATA_OUTPUTS / "fraud_alerts.csv", index=False)

    action_summary = alerts.groupby("payment_action", as_index=False).agg(
        transaction_count=("transaction_id", "count"),
        average_fraud_score=("fraud_score", "mean"),
        expected_fraud_loss=("expected_fraud_loss", "sum"),
        observed_fraud_rate=("fraud_flag", "mean"),
    )
    action_summary["transaction_share"] = action_summary["transaction_count"] / len(alerts)
    reason_frequency = (
        pd.concat([alerts["top_reason_1"], alerts["top_reason_2"], alerts["top_reason_3"]])
        .value_counts()
        .rename_axis("reason_code")
        .reset_index(name="count")
    )
    test_scores = alerts.loc[test_idx, "fraud_score"].to_numpy(float)
    test_amount = working.loc[test_idx, "amount"].to_numpy(float)
    tradeoff = threshold_tradeoff(y_test, test_scores, test_amount, np.linspace(0.10, 0.90, 17), fraud_test_probability)
    confusion = confusion_at_threshold(y_test, test_scores, 0.60)
    precision, recall = precision_recall_from_confusion(confusion)
    validation = {
        "train_idx": train_idx,
        "val_idx": val_idx,
        "test_idx": test_idx,
        "y_test": y_test,
        "test_scores": test_scores,
        "test_calibrated_scores": fraud_test_calibrated,
        "test_probability_scores": fraud_test_probability,
        "confusion": confusion,
        "precision": precision,
        "recall": recall,
        "pr_auc": pr_auc_score(y_test, test_scores),
        "supervised_probability_pr_auc": pr_auc_score(y_test, fraud_test_probability),
        "roc_auc": roc_auc_score(y_test, test_scores),
        "false_positive_rate": safe_divide(confusion["false_positive"], confusion["false_positive"] + confusion["true_negative"]),
        "false_negative_rate": safe_divide(confusion["false_negative"], confusion["false_negative"] + confusion["true_positive"]),
        "manual_review_volume": int((alerts["manual_review_priority"] > 0).sum()),
        "expected_fraud_loss_avoided": float(alerts.loc[alerts["payment_action"].isin(["Manual review", "Block"]), "expected_fraud_loss"].sum()),
        "feature_importance": supervised.coefficient_table(),
    }
    top_anomaly_cutoff = float(alerts["anomaly_score"].quantile(0.95))
    anomaly_flagged = alerts["anomaly_score"] >= top_anomaly_cutoff
    validation["anomaly_top_5pct_capture_rate"] = safe_divide(
        float(alerts.loc[anomaly_flagged, "fraud_flag"].sum()),
        float(alerts["fraud_flag"].sum()),
    )
    validation["anomaly_top_5pct_review_volume"] = int(anomaly_flagged.sum())
    fraud_policy_summary = {
        "payment_action_mix": round_records(action_summary),
        "fraud_score_distribution": summarize_distribution(alerts["fraud_score"], [0, 0.2, 0.35, 0.6, 0.8, 1], ["0-0.20", "0.20-0.35", "0.35-0.60", "0.60-0.80", "0.80-1.00"]),
        "expected_fraud_loss_by_action": round_records(action_summary[["payment_action", "expected_fraud_loss", "transaction_count"]]),
        "manual_review_queue_size": int((alerts["manual_review_priority"] > 0).sum()),
        "manual_review_capacity": review_capacity,
        "top_fraud_drivers": round_records(reason_frequency),
        "threshold_tradeoff": tradeoff,
        "metrics": {
            "PR_AUC": validation["pr_auc"],
            "supervised_probability_PR_AUC": validation["supervised_probability_pr_auc"],
            "precision": precision,
            "recall": recall,
            "fraud_capture_rate": recall,
            "false_positive_rate": validation["false_positive_rate"],
            "false_negative_rate": validation["false_negative_rate"],
            "expected_fraud_loss_avoided": validation["expected_fraud_loss_avoided"],
            "manual_review_volume": validation["manual_review_volume"],
            "ROC_AUC_secondary": validation["roc_auc"],
        },
        "assumptions": {
            "loss_severity": 0.90,
            "labels": "fraud_flag is synthetic and disclosed for portfolio demonstration.",
            "review_capacity": review_capacity,
        },
    }
    write_json(DATA_OUTPUTS / "fraud_policy_summary.json", fraud_policy_summary)
    write_json(
        DATA_OUTPUTS / "fraud_alerts.json",
        {
            "metadata": {
                "source": "data/outputs/fraud_alerts.csv",
                "synthetic_data_disclosure": "Transaction stream and fraud labels are synthetic.",
                "loss_severity_assumption": 0.90,
            },
            "records": round_records(alerts[output_columns].sort_values("fraud_score", ascending=False).head(700)),
            "charts": {
                "fraud_score_distribution": fraud_policy_summary["fraud_score_distribution"],
                "payment_action_mix": fraud_policy_summary["payment_action_mix"],
                "fraud_capture_vs_threshold": tradeoff,
                "false_positives_vs_threshold": tradeoff,
                "manual_review_volume_vs_threshold": tradeoff,
                "expected_fraud_loss_by_action": fraud_policy_summary["expected_fraud_loss_by_action"],
                "top_fraud_reason_code_frequency": fraud_policy_summary["top_fraud_drivers"],
            },
        },
    )
    return {"alerts": alerts, "validation": validation, "summary": fraud_policy_summary}


def stablecoin_action_from_score(score: float) -> str:
    if score < 0.40:
        return "Normal"
    if score < 0.65:
        return "Monitor"
    if score < 0.85:
        return "Review"
    return "High-risk wallet"


def stablecoin_reason_codes(row: pd.Series) -> list[str]:
    candidates = [
        (row["counterparty_risk_score"], "risky counterparty exposure"),
        (float(row["risky_address_exposure_flag"]), "risky address exposure"),
        (np.clip(row["wallet_velocity"] / 40, 0, 1), "high wallet velocity"),
        (row["counterparty_concentration"], "counterparty concentration"),
        (float(row["round_trip_proxy"]), "round-trip flow proxy"),
        (float(row["large_transfer_flag"]), "large transfer"),
        (float(row["new_counterparty_flag"]), "new counterparty"),
    ]
    return [label for _, label in sorted(candidates, key=lambda item: item[0], reverse=True)[:3]]


def build_stablecoin_module(stablecoin: pd.DataFrame) -> dict[str, Any]:
    alerts = stablecoin.copy()
    raw_score = (
        0.34 * alerts["counterparty_risk_score"]
        + 0.22 * alerts["risky_address_exposure_flag"]
        + 0.13 * np.clip(alerts["wallet_velocity"] / 40, 0, 1)
        + 0.11 * alerts["counterparty_concentration"]
        + 0.09 * alerts["round_trip_proxy"]
        + 0.06 * alerts["large_transfer_flag"]
        + 0.05 * alerts["new_counterparty_flag"]
    )
    score = np.clip(
        1.70 * raw_score + 0.05 * alerts["risky_address_exposure_flag"] + 0.03 * alerts["large_transfer_flag"],
        0,
        1,
    )
    alerts["stablecoin_risk_score"] = score
    alerts["stablecoin_risk_action"] = alerts["stablecoin_risk_score"].map(stablecoin_action_from_score)
    alerts["stablecoin_risk_exposure"] = alerts["stablecoin_risk_score"] * alerts["amount_usd"]
    reason_codes = alerts.apply(stablecoin_reason_codes, axis=1)
    alerts["top_reason_1"] = [codes[0] for codes in reason_codes]
    alerts["top_reason_2"] = [codes[1] for codes in reason_codes]
    alerts["top_reason_3"] = [codes[2] for codes in reason_codes]
    output_columns = [
        "wallet_id",
        "counterparty_wallet_id",
        "transaction_time",
        "amount_usd",
        "stablecoin_risk_score",
        "stablecoin_risk_action",
        "risk_exposure_score",
        "stablecoin_risk_exposure",
        "top_reason_1",
        "top_reason_2",
        "top_reason_3",
        "stablecoin_risk_label",
    ]
    alerts[output_columns].to_csv(DATA_OUTPUTS / "stablecoin_alerts.csv", index=False)
    action_summary = alerts.groupby("stablecoin_risk_action", as_index=False).agg(
        transaction_count=("wallet_id", "count"),
        average_risk_score=("stablecoin_risk_score", "mean"),
        risk_exposure=("stablecoin_risk_exposure", "sum"),
        high_risk_label_rate=("stablecoin_risk_label", "mean"),
    )
    action_summary["transaction_share"] = action_summary["transaction_count"] / len(alerts)
    reason_frequency = (
        pd.concat([alerts["top_reason_1"], alerts["top_reason_2"], alerts["top_reason_3"]])
        .value_counts()
        .rename_axis("reason_code")
        .reset_index(name="count")
    )
    leaderboard = alerts.sort_values("stablecoin_risk_exposure", ascending=False).head(25)[
        ["wallet_id", "counterparty_wallet_id", "amount_usd", "stablecoin_risk_score", "stablecoin_risk_action", "stablecoin_risk_exposure"]
    ]
    threshold_sensitivity = []
    for threshold in np.linspace(0.40, 0.90, 11):
        flagged = alerts["stablecoin_risk_score"] >= threshold
        threshold_sensitivity.append(
            {
                "threshold": round(float(threshold), 4),
                "flagged_transactions": int(flagged.sum()),
                "flagged_share": safe_divide(float(flagged.sum()), len(alerts)),
                "risky_exposure": float(alerts.loc[flagged, "stablecoin_risk_exposure"].sum()),
            }
        )
    validation = {
        "score_distribution": summarize_distribution(alerts["stablecoin_risk_score"], [0, 0.25, 0.4, 0.65, 0.85, 1], ["0-0.25", "0.25-0.40", "0.40-0.65", "0.65-0.85", "0.85-1.00"]),
        "risk_action_mix": round_records(action_summary),
        "high_risk_wallet_concentration": safe_divide(
            alerts.loc[alerts["stablecoin_risk_action"] == "High-risk wallet", "stablecoin_risk_exposure"].sum(),
            alerts["stablecoin_risk_exposure"].sum(),
        ),
        "risky_exposure_by_score_band": threshold_sensitivity,
        "threshold_sensitivity": threshold_sensitivity,
        "top_risk_driver_frequency": round_records(reason_frequency),
    }
    write_json(
        DATA_OUTPUTS / "stablecoin_alerts.json",
        {
            "metadata": {
                "source": "data/outputs/stablecoin_alerts.csv",
                "scope": "payments-risk monitoring using AML-style risk indicators; not a regulatory compliance tool.",
                "synthetic_data_disclosure": "Stablecoin transaction sample and labels are synthetic.",
            },
            "records": round_records(alerts[output_columns].sort_values("stablecoin_risk_score", ascending=False).head(400)),
            "summary": {
                "stablecoin_action_mix": round_records(action_summary),
                "high_risk_wallet_count": int((alerts["stablecoin_risk_action"] == "High-risk wallet").sum()),
                "risk_exposure_by_action": round_records(action_summary[["stablecoin_risk_action", "risk_exposure", "transaction_count"]]),
                "top_wallet_risk_drivers": round_records(reason_frequency),
            },
            "charts": {
                "stablecoin_risk_score_distribution": validation["score_distribution"],
                "stablecoin_action_mix": round_records(action_summary),
                "wallet_risk_leaderboard": round_records(leaderboard),
            },
        },
    )
    return {"alerts": alerts, "validation": validation}


def aggregate_loss(df: pd.DataFrame, group_col: str, loss_col: str, exposure_col: str, count_col: str) -> pd.DataFrame:
    grouped = df.groupby(group_col, dropna=False, as_index=False).agg(
        total_expected_loss=(loss_col, "sum"),
        average_expected_loss=(loss_col, "mean"),
        exposure=(exposure_col, "sum"),
        account_count=(count_col, "count"),
    )
    grouped["expected_loss_rate"] = grouped["total_expected_loss"] / grouped["exposure"].replace(0, np.nan)
    grouped["expected_loss_rate"] = grouped["expected_loss_rate"].fillna(0)
    return grouped.rename(columns={group_col: "segment_value"}).assign(segment_name=group_col)


def build_expected_loss_engine(
    underwriting: dict[str, Any],
    fraud: dict[str, Any],
    stablecoin: dict[str, Any],
    macro: pd.DataFrame,
) -> dict[str, Any]:
    decisions = underwriting["decisions"].copy()
    alerts = fraud["alerts"].copy()
    stable_alerts = stablecoin["alerts"].copy()
    applicant_loss = decisions[
        [
            "applicant_id",
            "PD",
            "LGD",
            "EAD",
            "expected_loss",
            "expected_loss_rate",
            "risk_grade",
            "decision",
            "credit_grade",
            "loan_purpose",
            "debt_to_income",
            "annual_income",
            "application_vintage",
        ]
    ].copy()
    applicant_loss["base_loss"] = applicant_loss["expected_loss"]
    applicant_loss["moderate_stress_loss"] = (np.minimum(applicant_loss["PD"] * 1.25, 1.0) * np.minimum(applicant_loss["LGD"] * 1.10, 1.0) * applicant_loss["EAD"]).round(2)
    applicant_loss["severe_stress_loss"] = (np.minimum(applicant_loss["PD"] * 1.60, 1.0) * np.minimum(applicant_loss["LGD"] * 1.25, 1.0) * applicant_loss["EAD"]).round(2)
    applicant_loss["income_band"] = pd.cut(
        applicant_loss["annual_income"],
        bins=[0, 50000, 85000, 130000, np.inf],
        labels=["<$50k", "$50k-$85k", "$85k-$130k", "$130k+"],
        include_lowest=True,
    ).astype(str)
    applicant_loss["debt_to_income_band"] = pd.cut(
        applicant_loss["debt_to_income"],
        bins=[0, 0.20, 0.35, 0.50, np.inf],
        labels=["<20%", "20%-35%", "35%-50%", "50%+"],
        include_lowest=True,
    ).astype(str)
    applicant_loss.to_csv(DATA_OUTPUTS / "expected_loss_applicant_level.csv", index=False)

    credit_segments = pd.concat(
        [
            aggregate_loss(applicant_loss, "risk_grade", "expected_loss", "EAD", "applicant_id"),
            aggregate_loss(applicant_loss, "decision", "expected_loss", "EAD", "applicant_id"),
            aggregate_loss(applicant_loss, "credit_grade", "expected_loss", "EAD", "applicant_id"),
            aggregate_loss(applicant_loss, "loan_purpose", "expected_loss", "EAD", "applicant_id"),
            aggregate_loss(applicant_loss, "income_band", "expected_loss", "EAD", "applicant_id"),
            aggregate_loss(applicant_loss, "debt_to_income_band", "expected_loss", "EAD", "applicant_id"),
            aggregate_loss(applicant_loss, "application_vintage", "expected_loss", "EAD", "applicant_id"),
        ],
        ignore_index=True,
    )
    payment_segment = aggregate_loss(
        alerts.assign(EAD=alerts["amount"]),
        "payment_action",
        "expected_fraud_loss",
        "EAD",
        "transaction_id",
    )
    merchant_segment = aggregate_loss(
        alerts.assign(EAD=alerts["amount"]),
        "merchant_risk_band",
        "expected_fraud_loss",
        "EAD",
        "transaction_id",
    )
    stable_segment = aggregate_loss(
        stable_alerts.assign(EAD=stable_alerts["amount_usd"]),
        "stablecoin_risk_action",
        "stablecoin_risk_exposure",
        "EAD",
        "wallet_id",
    )
    expected_loss_by_segment = {
        "credit_segments": round_records(credit_segments),
        "payment_segments": round_records(pd.concat([payment_segment, merchant_segment], ignore_index=True)),
        "stablecoin_segments": round_records(stable_segment),
    }
    write_json(DATA_OUTPUTS / "expected_loss_by_segment.json", expected_loss_by_segment)

    credit_total = float(applicant_loss["expected_loss"].sum())
    fraud_total = float(alerts["expected_fraud_loss"].sum())
    stable_total = float(stable_alerts["stablecoin_risk_exposure"].sum())
    approved_exposure = float(applicant_loss["EAD"].sum())
    stress_summary = []
    stress_definitions = {
        "Base": {"PD_multiplier": 1.00, "LGD_multiplier": 1.00, "fraud_loss_multiplier": 1.00, "stablecoin_risk_multiplier": 1.00},
        "Moderate Stress": {"PD_multiplier": 1.25, "LGD_multiplier": 1.10, "fraud_loss_multiplier": 1.20, "stablecoin_risk_multiplier": 1.10},
        "Severe Stress": {"PD_multiplier": 1.60, "LGD_multiplier": 1.25, "fraud_loss_multiplier": 1.50, "stablecoin_risk_multiplier": 1.25},
    }
    for scenario, multipliers in stress_definitions.items():
        credit_loss = float((np.minimum(applicant_loss["PD"] * multipliers["PD_multiplier"], 1.0) * np.minimum(applicant_loss["LGD"] * multipliers["LGD_multiplier"], 1.0) * applicant_loss["EAD"]).sum())
        fraud_loss = fraud_total * multipliers["fraud_loss_multiplier"]
        stable_exposure = stable_total * multipliers["stablecoin_risk_multiplier"]
        stress_summary.append(
            {
                "scenario": scenario,
                **multipliers,
                "expected_credit_loss": credit_loss,
                "expected_fraud_loss": fraud_loss,
                "stablecoin_risk_exposure": stable_exposure,
                "total_expected_loss": credit_loss + fraud_loss + stable_exposure,
            }
        )
    write_json(
        DATA_OUTPUTS / "stress_loss_summary.json",
        {
            "scenarios": stress_summary,
            "assumptions": {
                "PD_cap": 1.0,
                "stablecoin_risk_multiplier_note": "Stablecoin stress is a labeled proxy sensitivity, not realized AML loss.",
                "macro_inputs_source": "data/processed/macro_stress_inputs.csv",
                "macro_limitation": "Macro variables support stress overlays only and are not modeled as individual default causes.",
            },
            "macro_context": round_records(macro.tail(12)),
        },
    )
    waterfall = [
        {"component": "expected credit loss", "amount": credit_total},
        {"component": "expected fraud loss", "amount": fraud_total},
        {"component": "stablecoin risk exposure proxy", "amount": stable_total},
    ]
    summary = {
        "portfolio": {
            "base_expected_loss": credit_total + fraud_total + stable_total,
            "expected_credit_loss": credit_total,
            "expected_fraud_loss": fraud_total,
            "stablecoin_risk_exposure": stable_total,
            "approved_exposure": approved_exposure,
            "loss_rate": safe_divide(credit_total, approved_exposure),
        },
        "expected_loss_by_risk_grade": round_records(
            credit_segments[credit_segments["segment_name"] == "risk_grade"].sort_values("segment_value")
        ),
        "expected_loss_by_decision": round_records(
            credit_segments[credit_segments["segment_name"] == "decision"].sort_values("segment_value")
        ),
        "expected_loss_waterfall": waterfall,
        "fraud_loss_by_payment_action": round_records(payment_segment),
        "stablecoin_risk_exposure_by_action": round_records(stable_segment),
        "assumptions": {
            "formula": "Expected Loss = PD \\u00d7 LGD \\u00d7 EAD",
            "LGD": "35% for A-B, 55% for C-D, 75% for E; labeled assumption.",
            "EAD": "Installment-style EAD equals loan_amount for approved or reviewed applicants; declined applicants have zero approved exposure.",
            "fraud_loss_severity": "90% loss severity assumption.",
            "stablecoin_proxy": "Stablecoin Risk Exposure = stablecoin_risk_score \\u00d7 amount_usd; not realized loss.",
        },
    }
    write_json(DATA_OUTPUTS / "expected_loss_summary.json", summary)
    return {
        "applicant_loss": applicant_loss,
        "credit_segments": credit_segments,
        "payment_segment": payment_segment,
        "stable_segment": stable_segment,
        "summary": summary,
        "stress_summary": stress_summary,
    }


def simulator_row(
    decisions: pd.DataFrame,
    fraud_alerts: pd.DataFrame,
    stable_alerts: pd.DataFrame,
    verdicts: list[dict[str, Any]],
    scenario_id: str,
    credit_pd_cutoff: float,
    fraud_threshold: float,
    stablecoin_threshold: float,
    review_capacity: int,
    pd_multiplier: float,
    lgd_multiplier: float,
    fraud_multiplier: float,
    stable_multiplier: float,
) -> dict[str, Any]:
    pd_values = np.minimum(decisions["PD"] * pd_multiplier, 1.0)
    lgd_values = np.minimum(decisions["LGD"] * lgd_multiplier, 1.0)
    review_cutoff = min(credit_pd_cutoff + 0.06, 0.99)
    decision = np.where(pd_values < credit_pd_cutoff, "Approve", np.where(pd_values < review_cutoff, "Review", "Decline"))
    exposure = np.where(decision == "Decline", 0.0, decisions["loan_amount"])
    credit_loss = float((pd_values * lgd_values * exposure).sum())
    fraud_flagged = fraud_alerts["fraud_score"] >= fraud_threshold
    stable_flagged = stable_alerts["stablecoin_risk_score"] >= stablecoin_threshold
    expected_fraud_loss = float((fraud_alerts.loc[~fraud_flagged, "expected_fraud_loss"].sum()) * fraud_multiplier)
    stable_exposure = float(stable_alerts.loc[stable_flagged, "stablecoin_risk_exposure"].sum() * stable_multiplier)
    manual_review_volume = int(((decision == "Review").sum()) + fraud_flagged.sum())
    warnings = []
    if manual_review_volume > review_capacity:
        over = safe_divide(manual_review_volume - review_capacity, review_capacity)
        warnings.append(f"Manual review volume exceeds capacity by {over:.0%}.")
    if any(v["validation_verdict"] in {"Monitor", "Fail"} for v in verdicts):
        weak = ", ".join([v["model_name"] for v in verdicts if v["validation_verdict"] in {"Monitor", "Fail"}])
        warnings.append(f"Model validation verdict requires monitoring for {weak}.")
    if stable_exposure > stable_alerts["stablecoin_risk_exposure"].sum() * 0.5:
        warnings.append("Stablecoin high-risk exposure exceeds 50% of proxy exposure.")
    return {
        "scenario_id": scenario_id,
        "credit_pd_cutoff": credit_pd_cutoff,
        "fraud_threshold": fraud_threshold,
        "stablecoin_threshold": stablecoin_threshold,
        "approval_rate": safe_divide(float((decision == "Approve").sum()), len(decisions)),
        "review_rate": safe_divide(float((decision == "Review").sum()), len(decisions)),
        "decline_rate": safe_divide(float((decision == "Decline").sum()), len(decisions)),
        "approved_exposure": float(exposure.sum()),
        "expected_credit_loss": credit_loss,
        "expected_fraud_loss": expected_fraud_loss,
        "stablecoin_risk_exposure": stable_exposure,
        "total_expected_loss": credit_loss + expected_fraud_loss + stable_exposure,
        "loss_rate": safe_divide(credit_loss, float(exposure.sum())),
        "manual_review_volume": manual_review_volume,
        "blocked_transaction_rate": safe_divide(float((fraud_alerts["fraud_score"] >= 0.80).sum()), len(fraud_alerts)),
        "model_risk_flag": "Monitor" if warnings else "Pass",
        "model_risk_warnings": warnings,
    }


def build_policy_simulator_data(
    underwriting: dict[str, Any],
    fraud: dict[str, Any],
    stablecoin: dict[str, Any],
    validation_verdicts: list[dict[str, Any]],
) -> dict[str, Any]:
    decisions = underwriting["decisions"]
    fraud_alerts = fraud["alerts"]
    stable_alerts = stablecoin["alerts"]
    stress = {
        "Base": (1.0, 1.0, 1.0, 1.0),
        "Moderate Stress": (1.25, 1.10, 1.20, 1.10),
        "Severe Stress": (1.60, 1.25, 1.50, 1.25),
    }
    rows = []
    for pd_cutoff in [0.04, 0.05, 0.06, 0.08, 0.10]:
        for fraud_threshold in [0.35, 0.50, 0.60, 0.70, 0.80]:
            for stable_threshold in [0.40, 0.65, 0.75, 0.85]:
                scenario_id = f"pd{pd_cutoff:.2f}_fraud{fraud_threshold:.2f}_stable{stable_threshold:.2f}_base"
                rows.append(
                    simulator_row(
                        decisions,
                        fraud_alerts,
                        stable_alerts,
                        validation_verdicts,
                        scenario_id,
                        pd_cutoff,
                        fraud_threshold,
                        stable_threshold,
                        review_capacity=420,
                        pd_multiplier=1.0,
                        lgd_multiplier=1.0,
                        fraud_multiplier=1.0,
                        stable_multiplier=1.0,
                    )
                )
    for scenario_name, multipliers in stress.items():
        rows.append(
            simulator_row(
                decisions,
                fraud_alerts,
                stable_alerts,
                validation_verdicts,
                f"default_{scenario_name.lower().replace(' ', '_')}",
                0.06,
                0.60,
                0.65,
                review_capacity=420,
                pd_multiplier=multipliers[0],
                lgd_multiplier=multipliers[1],
                fraud_multiplier=multipliers[2],
                stable_multiplier=multipliers[3],
            )
        )
    grid = pd.DataFrame(rows)
    grid.to_csv(DATA_OUTPUTS / "policy_threshold_grid.csv", index=False)
    default_result = grid[grid["scenario_id"] == "default_base"].iloc[0].to_dict()
    controls = {
        "credit_policy_controls": {
            "approval_PD_cutoff": 0.06,
            "manual_review_PD_band": [0.06, 0.12],
            "decline_PD_cutoff": 0.12,
            "maximum_expected_loss_rate": 0.08,
            "minimum_risk_grade_allowed": "D",
            "credit_limit_multiplier": 1.00,
        },
        "fraud_policy_controls": {
            "approve_threshold": 0.00,
            "step_up_threshold": 0.35,
            "manual_review_threshold": 0.60,
            "block_threshold": 0.80,
            "manual_review_capacity": 420,
            "fraud_loss_severity": 0.90,
        },
        "stablecoin_policy_controls": {
            "monitor_threshold": 0.40,
            "review_threshold": 0.65,
            "high_risk_wallet_threshold": 0.85,
            "risky_counterparty_tolerance": 0.70,
            "wallet_velocity_tolerance": 40,
        },
        "stress_controls": {
            "Base": {"PD_multiplier": 1.00, "LGD_multiplier": 1.00, "fraud_loss_multiplier": 1.00, "stablecoin_risk_multiplier": 1.00},
            "Moderate Stress": {"PD_multiplier": 1.25, "LGD_multiplier": 1.10, "fraud_loss_multiplier": 1.20, "stablecoin_risk_multiplier": 1.10},
            "Severe Stress": {"PD_multiplier": 1.60, "LGD_multiplier": 1.25, "fraud_loss_multiplier": 1.50, "stablecoin_risk_multiplier": 1.25},
        },
        "constraint_rules": {
            "credit": "approve cutoff < review cutoff < decline cutoff",
            "fraud": "approve threshold < step-up threshold < review threshold < block threshold",
            "stablecoin": "monitor threshold < review threshold < high-risk threshold",
        },
    }
    tradeoff_views = {
        "approval_rate_vs_expected_loss": round_records(grid.groupby("credit_pd_cutoff", as_index=False).agg(approval_rate=("approval_rate", "mean"), expected_credit_loss=("expected_credit_loss", "mean"))),
        "pd_cutoff_vs_loss_rate": round_records(grid.groupby("credit_pd_cutoff", as_index=False).agg(loss_rate=("loss_rate", "mean"))),
        "fraud_threshold_vs_expected_fraud_loss": round_records(grid.groupby("fraud_threshold", as_index=False).agg(expected_fraud_loss=("expected_fraud_loss", "mean"), manual_review_volume=("manual_review_volume", "mean"))),
        "stablecoin_threshold_vs_risky_exposure": round_records(grid.groupby("stablecoin_threshold", as_index=False).agg(stablecoin_risk_exposure=("stablecoin_risk_exposure", "mean"))),
        "stress_severity_vs_total_expected_loss": round_records(grid[grid["scenario_id"].str.startswith("default_")][["scenario_id", "total_expected_loss"]]),
    }
    write_json(DATA_OUTPUTS / "policy_simulator_inputs.json", {"controls": controls, "tradeoff_views": tradeoff_views})
    write_json(DATA_OUTPUTS / "policy_simulator_results.json", {"default_result": as_builtin(default_result), "scenarios": round_records(grid)})
    write_json(DATA_OUTPUTS / "policy_loss_comparison.json", {"scenarios": round_records(grid), "tradeoff_views": tradeoff_views})
    return {"grid": grid, "default_result": default_result, "controls": controls}


def validation_verdict(
    model_name: str,
    model_type: str,
    primary_metric: float,
    calibration_status: str,
    stability_status: str,
    segment_status: str,
    explainability_status: str,
    warning_reason: str | None = None,
) -> dict[str, Any]:
    statuses = [calibration_status, stability_status, segment_status, explainability_status]
    if any(status.lower().startswith("fail") for status in statuses):
        verdict = "Fail"
    elif warning_reason or any("monitor" in status.lower() or "weak" in status.lower() for status in statuses):
        verdict = "Monitor"
    else:
        verdict = "Pass"
    if warning_reason:
        reason = warning_reason
    elif verdict == "Pass":
        reason = f"{model_name} has acceptable metric evidence, calibration, stability, and explainability for this synthetic decision workflow."
    elif verdict == "Monitor":
        reason = f"{model_name} is usable for this demonstration with a documented validation weakness."
    else:
        reason = f"{model_name} is not reliable for decision use under the measured validation checks."
    return {
        "model_name": model_name,
        "model_type": model_type,
        "primary_metric": round(float(primary_metric), 6) if not np.isnan(primary_metric) else None,
        "calibration_status": calibration_status,
        "stability_status": stability_status,
        "segment_status": segment_status,
        "explainability_status": explainability_status,
        "validation_verdict": verdict,
        "verdict_reason": reason,
    }


def build_model_validation(
    credit: pd.DataFrame,
    underwriting: dict[str, Any],
    fraud: dict[str, Any],
    stablecoin: dict[str, Any],
    expected_loss: dict[str, Any],
) -> dict[str, Any]:
    cv = underwriting["validation"]
    decisions = underwriting["decisions"]
    y_test = cv["y_test"]
    champion_pd = cv["champion_test_pd"]
    challenger_pd = cv["challenger_test_pd"]
    champion_auc = roc_auc_score(y_test, champion_pd)
    challenger_auc = roc_auc_score(y_test, challenger_pd)
    champion_pr = pr_auc_score(y_test, champion_pd)
    challenger_pr = pr_auc_score(y_test, challenger_pd)
    champion_brier = brier_score(y_test, champion_pd)
    challenger_brier = brier_score(y_test, challenger_pd)
    champion_ks = ks_statistic(y_test, champion_pd)
    champion_psi = population_stability_index(cv["champion_train_pd"], champion_pd)
    calibration = cv["calibration_table"].copy()
    max_calibration_gap = float(calibration["calibration_gap"].abs().max())
    calibration_status = "Pass" if max_calibration_gap <= 0.075 else "Monitor: calibration gap exceeds 7.5 percentage points"
    stability = psi_status(champion_psi)
    stability_status = "Pass" if stability == "stable" else f"Monitor: PSI indicates {stability}"
    segment_rows = []
    for segment in ["credit_grade", "loan_purpose", "risk_grade", "application_vintage"]:
        for value, group in decisions.groupby(segment):
            metric = roc_auc_score(group["default_flag"].to_numpy(int), group["PD"].to_numpy(float)) if group["default_flag"].nunique() > 1 else np.nan
            segment_rows.append(
                {
                    "model_name": "champion_logistic_scorecard",
                    "model_type": "logistic regression scorecard",
                    "validation_view": "segment",
                    "segment": segment,
                    "segment_value": value,
                    "segment_count": int(len(group)),
                    "event_rate": float(group["default_flag"].mean()),
                    "average_score": float(group["PD"].mean()),
                    "model_metric_by_segment": metric,
                    "expected_loss_by_segment": float(group["expected_loss"].sum()),
                    "decision_rate_by_segment": safe_divide(float((group["decision"] == "Approve").sum()), len(group)),
                    "status": "Monitor" if len(group) < 50 or (not np.isnan(metric) and metric < 0.55) else "Pass",
                }
            )
    credit_validation_rows = [
        {
            "model_name": "champion_logistic_scorecard",
            "model_type": "logistic regression scorecard",
            "validation_view": "overall",
            "segment": "all",
            "segment_value": "all",
            "segment_count": int(len(y_test)),
            "event_rate": float(y_test.mean()),
            "average_score": float(champion_pd.mean()),
            "model_metric_by_segment": champion_auc,
            "expected_loss_by_segment": float(decisions["expected_loss"].sum()),
            "decision_rate_by_segment": safe_divide(float((decisions["decision"] == "Approve").sum()), len(decisions)),
            "status": "Pass",
        }
    ] + segment_rows
    credit_validation_df = pd.DataFrame(credit_validation_rows)
    credit_validation_df.to_csv(DATA_OUTPUTS / "credit_model_validation.csv", index=False)

    fv = fraud["validation"]
    fraud_rows = [
        {
            "model_name": "fraud_supervised_logistic",
            "model_type": "logistic regression",
            "validation_view": "overall",
            "segment": "all",
            "segment_value": "all",
            "segment_count": int(len(fv["y_test"])),
            "event_rate": float(fv["y_test"].mean()),
            "average_score": float(fv["test_scores"].mean()),
            "PR_AUC": fv["pr_auc"],
            "precision": fv["precision"],
            "recall": fv["recall"],
            "false_positive_rate": fv["false_positive_rate"],
            "false_negative_rate": fv["false_negative_rate"],
            "manual_review_volume": fv["manual_review_volume"],
            "expected_fraud_loss_avoided": fv["expected_fraud_loss_avoided"],
            "status": "Pass" if fv["pr_auc"] > max(0.10, fv["y_test"].mean() * 2) else "Monitor",
        }
    ]
    fraud_alerts = fraud["alerts"]
    for value, group in fraud_alerts.groupby("merchant_risk_band"):
        fraud_rows.append(
            {
                "model_name": "fraud_supervised_logistic",
                "model_type": "logistic regression",
                "validation_view": "segment",
                "segment": "merchant_risk_band",
                "segment_value": value,
                "segment_count": int(len(group)),
                "event_rate": float(group["fraud_flag"].mean()),
                "average_score": float(group["fraud_score"].mean()),
                "PR_AUC": np.nan,
                "precision": np.nan,
                "recall": np.nan,
                "false_positive_rate": np.nan,
                "false_negative_rate": np.nan,
                "manual_review_volume": int((group["manual_review_priority"] > 0).sum()),
                "expected_fraud_loss_avoided": float(group.loc[group["payment_action"].isin(["Manual review", "Block"]), "expected_fraud_loss"].sum()),
                "status": "Pass" if len(group) >= 100 else "Monitor",
            }
        )
    fraud_validation_df = pd.DataFrame(fraud_rows)
    fraud_validation_df.to_csv(DATA_OUTPUTS / "fraud_model_validation.csv", index=False)

    stable_alerts = stablecoin["alerts"]
    stable_rows = []
    for action, group in stable_alerts.groupby("stablecoin_risk_action"):
        stable_rows.append(
            {
                "model_name": "stablecoin_rule_risk_score",
                "model_type": "rule-based payments risk score",
                "validation_view": "risk_action",
                "segment": "stablecoin_risk_action",
                "segment_value": action,
                "segment_count": int(len(group)),
                "event_rate": float(group["stablecoin_risk_label"].mean()),
                "average_score": float(group["stablecoin_risk_score"].mean()),
                "risky_exposure": float(group["stablecoin_risk_exposure"].sum()),
                "decision_rate_by_segment": safe_divide(float((group["stablecoin_risk_action"].isin(["Review", "High-risk wallet"])).sum()), len(group)),
                "status": "Pass" if len(group) >= 20 else "Monitor",
            }
        )
    stable_validation_df = pd.DataFrame(stable_rows)
    stable_validation_df.to_csv(DATA_OUTPUTS / "stablecoin_model_validation.csv", index=False)

    fraud_primary_status = "Pass" if fv["pr_auc"] > max(0.10, fv["y_test"].mean() * 2) else "Monitor: PR-AUC is weak for an imbalanced target"
    anomaly_capture = fv["anomaly_top_5pct_capture_rate"]
    anomaly_warning = None if anomaly_capture >= 0.20 else "Fraud anomaly score requires monitoring because top-score capture is below 20%."
    stable_primary_metric = safe_divide(
        stable_alerts.loc[stable_alerts["stablecoin_risk_action"].isin(["Monitor", "Review", "High-risk wallet"]), "stablecoin_risk_label"].sum(),
        stable_alerts["stablecoin_risk_label"].sum(),
    )
    verdicts = [
        validation_verdict(
            "champion_logistic_scorecard",
            "logistic regression scorecard",
            champion_auc,
            calibration_status,
            stability_status,
            "Pass" if credit_validation_df["status"].eq("Pass").mean() >= 0.85 else "Monitor: weak segment performance found",
            "Pass: coefficient table and reason codes exported",
        ),
        validation_verdict(
            "challenger_gradient_boosting",
            "gradient boosting model",
            challenger_auc,
            "Pass" if challenger_brier <= champion_brier + 0.03 else "Monitor: challenger calibration trails champion",
            "Pass",
            "Pass",
            "Monitor: feature importance is less transparent than scorecard",
            warning_reason="Challenger is retained as benchmark because explainability is weaker than the champion scorecard.",
        ),
        validation_verdict(
            "fraud_supervised_logistic",
            "logistic regression fraud model",
            fv["pr_auc"],
            "Pass: fraud score is calibrated with validation bins",
            "Pass",
            fraud_primary_status,
            "Pass: rules and coefficient drivers exported",
            warning_reason=None if fraud_primary_status == "Pass" else "Fraud model requires monitoring because imbalanced-target PR-AUC is weak.",
        ),
        validation_verdict(
            "fraud_anomaly_rules",
            "robust z-score anomaly model",
            anomaly_capture,
            "Pass: anomaly score is a normalized risk score, not PD",
            "Pass",
            "Pass" if anomaly_capture >= 0.20 else "Monitor: weak anomaly capture in top-score band",
            "Pass: rule triggers exported",
            warning_reason=anomaly_warning,
        ),
        validation_verdict(
            "stablecoin_rule_risk_score",
            "rule-based payments risk score",
            stable_primary_metric,
            "Pass: stablecoin score is not represented as calibrated PD",
            "Pass",
            "Pass",
            "Pass: AML-style risk indicator drivers exported",
            warning_reason="Stablecoin score remains Monitor because labels are synthetic and the module is a secondary payments-risk proxy.",
        ),
    ]
    verdicts_df = pd.DataFrame(verdicts)
    if verdicts_df["validation_verdict"].isna().any():
        raise RuntimeError("Validation verdict generation failed.")
    write_json(DATA_OUTPUTS / "model_risk_verdicts.json", {"verdicts": verdicts})

    champion_challenger = {
        "comparison": [
            {
                "model_name": "champion_logistic_scorecard",
                "ROC_AUC": champion_auc,
                "PR_AUC": champion_pr,
                "Brier_score": champion_brier,
                "KS_statistic": champion_ks,
                "calibration_quality": calibration_status,
                "expected_loss_separation": float(decisions.groupby("risk_grade")["expected_loss"].mean().max() - decisions.groupby("risk_grade")["expected_loss"].mean().min()),
                "explainability": "High: standardized coefficients and reason codes",
                "stability": stability_status,
                "segment_weakness": "Monitor" if credit_validation_df["status"].eq("Monitor").any() else "None flagged",
            },
            {
                "model_name": "challenger_gradient_boosting",
                "ROC_AUC": challenger_auc,
                "PR_AUC": challenger_pr,
                "Brier_score": challenger_brier,
                "KS_statistic": ks_statistic(y_test, challenger_pd),
                "calibration_quality": "Pass" if challenger_brier <= champion_brier + 0.03 else "Monitor",
                "expected_loss_separation": "benchmark only",
                "explainability": "Medium: feature importance, no scorecard coefficients",
                "stability": "Pass",
                "segment_weakness": "Not selected for policy",
            },
        ],
        "selected_model": "champion_logistic_scorecard",
        "selection_reason": "Champion selected for calibrated PD, explainability, and reason-code support rather than highest-AUC selection alone.",
    }
    write_json(DATA_OUTPUTS / "champion_challenger_comparison.json", champion_challenger)

    score_drift = {
        "champion_train_test_PSI": champion_psi,
        "PSI_interpretation": psi_status(champion_psi),
        "target_rate_shift": float(credit.loc[cv["test_idx"], "default_flag"].mean() - credit.loc[cv["train_idx"], "default_flag"].mean()),
    }
    model_validation_summary = {
        "credit_model_metrics": {
            "ROC_AUC": champion_auc,
            "PR_AUC": champion_pr,
            "Brier_score": champion_brier,
            "KS_statistic": champion_ks,
            "confusion_matrix_at_policy_threshold": confusion_at_threshold(y_test, champion_pd, 0.12),
            "calibration_curve": round_records(calibration),
            "decile_default_table": round_records(calibration),
            "approval_rate_loss_rate_tradeoff": underwriting["summary"]["charts"]["approval_rate_vs_expected_loss"],
        },
        "fraud_model_metrics": {
            "PR_AUC": fv["pr_auc"],
            "supervised_probability_PR_AUC": fv["supervised_probability_pr_auc"],
            "precision": fv["precision"],
            "recall": fv["recall"],
            "fraud_capture_rate": fv["recall"],
            "false_positive_rate": fv["false_positive_rate"],
            "false_negative_rate": fv["false_negative_rate"],
            "manual_review_volume": fv["manual_review_volume"],
            "expected_fraud_loss_avoided": fv["expected_fraud_loss_avoided"],
            "ROC_AUC_secondary": fv["roc_auc"],
            "confusion_matrix": fv["confusion"],
            "anomaly_top_5pct_capture_rate": fv["anomaly_top_5pct_capture_rate"],
            "anomaly_top_5pct_review_volume": fv["anomaly_top_5pct_review_volume"],
        },
        "stablecoin_risk_validation": stablecoin["validation"],
        "stability_and_drift": score_drift,
        "segment_level_validation": {
            "credit": round_records(credit_validation_df),
            "fraud": round_records(fraud_validation_df),
            "stablecoin": round_records(stable_validation_df),
        },
        "explainability": {
            "credit_feature_importance": round_records(cv["champion_coefficients"].head(20)),
            "challenger_feature_importance": round_records(cv["challenger_importance"].head(20)),
            "fraud_feature_importance": round_records(fv["feature_importance"].head(20)),
            "reason_code_frequency": underwriting["summary"]["charts"]["top_reason_code_frequency"][:15],
            "example_applicant_explanation": round_records(decisions.sort_values("PD", ascending=False).head(1)[["applicant_id", "PD", "decision", "top_reason_1", "top_reason_2", "top_reason_3"]]),
            "example_transaction_explanation": round_records(fraud["alerts"].sort_values("fraud_score", ascending=False).head(1)[["transaction_id", "fraud_score", "payment_action", "top_reason_1", "top_reason_2", "top_reason_3"]]),
        },
        "champion_vs_challenger": champion_challenger,
        "model_verdicts": verdicts,
        "charts": {
            "credit_calibration_curve": round_records(calibration),
            "PD_decile_default_table": round_records(calibration),
            "champion_vs_challenger_comparison": champion_challenger["comparison"],
            "score_drift_chart": score_drift,
            "PSI_summary": [{"model": "champion_logistic_scorecard", "PSI": champion_psi, "status": psi_status(champion_psi)}],
            "segment_performance_heatmap": round_records(credit_validation_df),
            "fraud_precision_recall_curve": fraud["summary"]["threshold_tradeoff"],
            "fraud_threshold_tradeoff": fraud["summary"]["threshold_tradeoff"],
            "stablecoin_risk_distribution": stablecoin["validation"]["score_distribution"],
            "model_verdict_panel": verdicts,
        },
    }
    write_json(DATA_OUTPUTS / "model_validation_summary.json", model_validation_summary)
    return {
        "verdicts": verdicts,
        "summary": model_validation_summary,
        "credit_validation_df": credit_validation_df,
        "fraud_validation_df": fraud_validation_df,
        "stable_validation_df": stable_validation_df,
    }


def verify_reconciliation(
    underwriting: dict[str, Any],
    fraud: dict[str, Any],
    stablecoin: dict[str, Any],
    expected_loss: dict[str, Any],
    simulator: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    decisions = underwriting["decisions"]
    alerts = fraud["alerts"]
    stable_alerts = stablecoin["alerts"]
    applicant_loss = expected_loss["applicant_loss"]
    if len(decisions) != len(applicant_loss):
        raise RuntimeError("Applicant totals do not reconcile.")
    if not np.isclose(decisions["expected_loss"].sum(), applicant_loss["expected_loss"].sum(), atol=1.0):
        raise RuntimeError("Expected credit loss totals do not reconcile.")
    if not np.isclose(alerts["expected_fraud_loss"].sum(), expected_loss["summary"]["portfolio"]["expected_fraud_loss"], atol=1.0):
        raise RuntimeError("Fraud loss totals do not reconcile.")
    if not np.isclose(stable_alerts["stablecoin_risk_exposure"].sum(), expected_loss["summary"]["portfolio"]["stablecoin_risk_exposure"], atol=1.0):
        raise RuntimeError("Stablecoin exposure totals do not reconcile.")
    for segment_name, group in expected_loss["credit_segments"].groupby("segment_name"):
        total = group["total_expected_loss"].sum()
        if not np.isclose(total, applicant_loss["expected_loss"].sum(), atol=2.0):
            raise RuntimeError(f"Credit segment totals do not reconcile for {segment_name}.")
    if simulator["grid"]["scenario_id"].duplicated().any():
        raise RuntimeError("Policy simulator scenario IDs are not unique.")
    allowed = {"Pass", "Monitor", "Fail"}
    if any(v["validation_verdict"] not in allowed for v in validation["verdicts"]):
        raise RuntimeError("Validation verdicts contain unsupported values.")


def build_reporting_outputs(
    data: dict[str, pd.DataFrame],
    underwriting: dict[str, Any],
    fraud: dict[str, Any],
    stablecoin: dict[str, Any],
    expected_loss: dict[str, Any],
    validation: dict[str, Any],
    simulator: dict[str, Any],
) -> None:
    decisions = underwriting["decisions"]
    fraud_alerts = fraud["alerts"]
    stable_alerts = stablecoin["alerts"]
    verdicts = validation["verdicts"]
    verdict_summary = pd.DataFrame(verdicts)["validation_verdict"].value_counts().to_dict()
    highest_segment = expected_loss["credit_segments"].sort_values("expected_loss_rate", ascending=False).head(1).iloc[0]
    command_center = {
        "total_applicants": int(len(decisions)),
        "approval_rate": safe_divide(float((decisions["decision"] == "Approve").sum()), len(decisions)),
        "review_rate": safe_divide(float((decisions["decision"] == "Review").sum()), len(decisions)),
        "decline_rate": safe_divide(float((decisions["decision"] == "Decline").sum()), len(decisions)),
        "average_PD": float(decisions["PD"].mean()),
        "total_approved_exposure": float(decisions["EAD"].sum()),
        "total_expected_credit_loss": float(decisions["expected_loss"].sum()),
        "total_expected_fraud_loss": float(fraud_alerts["expected_fraud_loss"].sum()),
        "stablecoin_risk_exposure": float(stable_alerts["stablecoin_risk_exposure"].sum()),
        "manual_review_volume": int((decisions["decision"] == "Review").sum() + (fraud_alerts["manual_review_priority"] > 0).sum()),
        "model_verdict_summary": verdict_summary,
        "highest_risk_segment": {
            "segment_name": highest_segment["segment_name"],
            "segment_value": highest_segment["segment_value"],
            "expected_loss_rate": float(highest_segment["expected_loss_rate"]),
        },
        "data_model_disclaimer": "All applicant, payment, stablecoin, and label data are synthetic and used for decision-engine demonstration only.",
    }
    write_json(DATA_OUTPUTS / "risk_command_center.json", command_center)
    methodology = {
        "data_sources": {
            "credit_applicants": "synthetic consumer credit applicant sample generated by src/build_backend.py",
            "payment_transactions": "synthetic card/payment transaction stream generated by src/build_backend.py",
            "stablecoin_transactions": "synthetic stablecoin payments-risk sample generated by src/build_backend.py",
            "macro_stress_inputs": "synthetic macro/stress overlay inputs generated by src/build_backend.py",
        },
        "synthetic_data_disclosure": "All data and labels are synthetic. Values are not presented as proprietary bank history or observed blockchain facts.",
        "model_list": [
            "champion logistic regression scorecard",
            "challenger gradient boosting model using decision stumps",
            "fraud supervised logistic regression",
            "fraud anomaly score using robust z-score rules",
            "stablecoin rule-based payments-risk score",
        ],
        "feature_summary": {
            "credit": "Application-time borrower, loan, utilization, delinquency, and affordability features; post-origination fields excluded.",
            "fraud": "Transaction-time amount, velocity, merchant, device, location, tenure, and anomaly features; chargeback outcome excluded from scoring.",
            "stablecoin": "Wallet velocity, counterparty risk, flow proxy, concentration, large transfer, and new counterparty indicators.",
        },
        "split_method": "Time-aware split: earliest 70% train, next 15% validation, latest 15% test where date fields exist.",
        "loss_assumptions": expected_loss["summary"]["assumptions"],
        "stress_assumptions": {
            "Base": "PD 1.00, LGD 1.00, fraud loss 1.00",
            "Moderate Stress": "PD 1.25, LGD 1.10, fraud loss 1.20, stablecoin proxy 1.10",
            "Severe Stress": "PD 1.60, LGD 1.25, fraud loss 1.50, stablecoin proxy 1.25",
        },
        "validation_methods": [
            "ROC-AUC, PR-AUC, Brier score, KS statistic",
            "calibration curve and decile default table",
            "PSI score drift check",
            "segment-level performance checks",
            "reason-code and feature-importance review",
            "threshold and policy tradeoff analysis",
        ],
        "known_limitations": [
            "Synthetic data supports portfolio demonstration, not production readiness.",
            "LGD, EAD, fraud severity, and stablecoin risk exposure are assumption-driven.",
            "Macro inputs are used only for stress overlays and not causal individual-default modeling.",
            "Stablecoin module uses AML-style risk indicators and is not a regulatory compliance tool.",
            "No claim is made that any policy is optimal without explicit constraints.",
        ],
    }
    write_json(DATA_OUTPUTS / "methodology_summary.json", methodology)


def required_output_check() -> None:
    required_files = [
        DATA_PROCESSED / "processed_credit_applicants.csv",
        DATA_PROCESSED / "processed_payment_transactions.csv",
        DATA_PROCESSED / "processed_stablecoin_transactions.csv",
        DATA_PROCESSED / "macro_stress_inputs.csv",
        DATA_PROCESSED / "underwriting_model_dataset.csv",
        DATA_PROCESSED / "fraud_model_dataset.csv",
        DATA_PROCESSED / "validation_dataset.csv",
        DATA_OUTPUTS / "underwriting_decisions.csv",
        DATA_OUTPUTS / "fraud_alerts.csv",
        DATA_OUTPUTS / "stablecoin_alerts.csv",
        DATA_OUTPUTS / "expected_loss_applicant_level.csv",
        DATA_OUTPUTS / "credit_model_validation.csv",
        DATA_OUTPUTS / "fraud_model_validation.csv",
        DATA_OUTPUTS / "stablecoin_model_validation.csv",
        DATA_OUTPUTS / "policy_threshold_grid.csv",
        DATA_OUTPUTS / "data_quality_report.csv",
        DATA_OUTPUTS / "risk_command_center.json",
        DATA_OUTPUTS / "underwriting_decisions.json",
        DATA_OUTPUTS / "underwriting_policy_summary.json",
        DATA_OUTPUTS / "fraud_alerts.json",
        DATA_OUTPUTS / "stablecoin_alerts.json",
        DATA_OUTPUTS / "fraud_policy_summary.json",
        DATA_OUTPUTS / "expected_loss_summary.json",
        DATA_OUTPUTS / "expected_loss_by_segment.json",
        DATA_OUTPUTS / "stress_loss_summary.json",
        DATA_OUTPUTS / "policy_loss_comparison.json",
        DATA_OUTPUTS / "policy_simulator_inputs.json",
        DATA_OUTPUTS / "policy_simulator_results.json",
        DATA_OUTPUTS / "model_validation_summary.json",
        DATA_OUTPUTS / "champion_challenger_comparison.json",
        DATA_OUTPUTS / "model_risk_verdicts.json",
        DATA_OUTPUTS / "methodology_summary.json",
        DATA_OUTPUTS / "calibration_curve.json",
        DATA_OUTPUTS / "decile_default_table.csv",
    ]
    missing = [path for path in required_files if not path.exists()]
    if missing:
        raise RuntimeError("Missing required outputs: " + ", ".join(str(path.relative_to(ROOT)) for path in missing))
    if (ROOT / "README.md").exists():
        raise RuntimeError("README.md exists but the build instructions forbid creating it.")


def main() -> None:
    ensure_dirs()
    data = build_data_layer()
    underwriting = build_underwriting_engine(data["credit"])
    fraud = build_fraud_engine(data["payments"])
    stablecoin = build_stablecoin_module(data["stablecoin"])
    expected_loss = build_expected_loss_engine(underwriting, fraud, stablecoin, data["macro"])
    validation = build_model_validation(data["credit"], underwriting, fraud, stablecoin, expected_loss)
    simulator = build_policy_simulator_data(underwriting, fraud, stablecoin, validation["verdicts"])
    verify_reconciliation(underwriting, fraud, stablecoin, expected_loss, simulator, validation)
    build_reporting_outputs(data, underwriting, fraud, stablecoin, expected_loss, validation, simulator)
    required_output_check()
    print("Backend build complete. Required processed and output artifacts are in data/processed and data/outputs.")


if __name__ == "__main__":
    main()
