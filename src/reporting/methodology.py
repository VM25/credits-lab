"""Methodology summary (doc 08 §12).

Full, honest disclosure of data sources, synthetic content, models, assumptions,
validation methods, the chart-data embedding map, and known limitations. No
overclaiming; no forbidden terms (production-ready, institutional-grade, AML
compliance, guaranteed, optimal, real-time bank).
"""
from src import config
from src.reporting.writers import write_json


def build() -> dict:
    fred_pull = "unknown"
    try:
        fred_pull = (config.RAW / "fred_pull_date.txt").read_text().strip()
    except OSError:
        pass

    methodology = {
        "data_sources": {
            "credit": "LendingClub accepted loans (public, Kaggle wordsforthewise/lending-club), seeded stratified sample.",
            "credit_rejects": "LendingClub rejected applicants (real) + clearly-labeled synthetic rejects for reject-inference/policy context only (never used for supervised PD training).",
            "card_payments": "Kaggle credit-card fraud (mlg-ulb/creditcardfraud) — real labels/amount/Time/V1..V28; deterministically downsampled (all fraud kept).",
            "stablecoin": "Fully synthetic, seeded transaction sample (secondary module).",
            "macro": f"FRED public series (UNRATE, FEDFUNDS, CPIAUCSL->YoY inflation, DRCCLACBS, CORCCACBS); pulled {fred_pull}. Used for stress overlays only.",
        },
        "synthetic_data_disclosure": {
            "fully_synthetic": ["stablecoin transactions", "synthetic rejected applicants"],
            "synthetic_features_on_real_records": [
                "card payments: merchant_category/merchant_risk_band/location_proxy/device_proxy/account_id/account_age_days and 24h velocity are synthetic context attached to REAL fraud labels + amount + PCA features"],
            "statement": "Synthetic data and engineered features are clearly labeled and never presented as observed history.",
        },
        "default_flag_definition": "Default / SEVERE-DELINQUENCY PROXY (not pure charge-off): 1 = Charged Off / Default / Late (31-120 days) / 'Does not meet the credit policy. Status:Charged Off'; 0 = Fully Paid; in-progress/ambiguous statuses dropped.",
        "model_list": {
            "underwriting_champion": "Logistic-regression scorecard (StandardScaler + LogisticRegression), isotonic-calibrated PD.",
            "underwriting_challenger": "Gradient boosting (sklearn), isotonic-calibrated; compared but not selected (explainability).",
            "fraud_supervised": "Logistic regression (class-weight balanced) on V1..V28 + engineered features.",
            "fraud_anomaly": "Isolation Forest (normalized anomaly score).",
            "stablecoin_scoring": "Transparent composite of AML-style risk indicators (not a trained classifier; synthetic label used only for validation).",
        },
        "feature_summary": "Application-time credit features (leakage-guarded; post-origination fields excluded) + engineered ratios/bands; payment V1..V28 + velocity/zscore/flags (fraud_flag & chargeback_loss excluded from features).",
        "split_method": "Time-aware 70/15/15 by date (credit issue_d; payments Time). Thresholds never tuned on the test split.",
        "loss_assumptions": {
            "lgd_by_risk": config.LGD_BY_RISK, "lgd_default": config.LGD_DEFAULT,
            "ead": "Installment EAD = loan_amount; revolving EAD = limit * utilization.",
            "utilization_assumption": config.UTILIZATION_ASSUMPTION,
            "fraud_loss_severity": config.FRAUD_LOSS_SEVERITY,
            "stablecoin_exposure": "risk_exposure = stablecoin_risk_score * amount_usd (exposure proxy, not realized loss).",
        },
        "stress_assumptions": config.STRESS,
        "operating_point": {
            "decision_thresholds": {"approve": config.PD_APPROVE, "decline": config.PD_DECLINE},
            "rationale": "Validation-derived for the high-base-rate accepted book (model rank-orders/calibrates well); doc reference cutoffs (approve<0.06/decline>=0.12) retained for the policy simulator.",
            "doc_reference_thresholds": config.DOC_REFERENCE_PD_THRESHOLDS,
            "risk_grade_bands": "Rescaled from doc starting bands to spread across the population PD distribution.",
        },
        "validation_methods": "ROC-AUC, PR-AUC (fraud headline), Brier, KS, calibration curve, decile default table, PSI/drift, segment performance, champion-vs-challenger, Pass/Monitor/Fail verdicts. Accuracy is not used as a headline metric for imbalanced fraud.",
        "chart_data_embedding_map": {
            "calibration_curve": "embedded in model_validation_summary.json (no standalone calibration_curve.json)",
            "decile_default_table": "embedded in model_validation_summary.json and credit_model_validation.csv (no standalone decile_default_table.csv)",
            "note": "Per the output contract, chart-ready structure lives inside the required JSON files; no extra output files are created.",
        },
        "known_limitations": [
            "default_flag is a default/severe-delinquency proxy, not pure charge-off.",
            "Credit champion discrimination is modest (ROC-AUC ~0.69); verdict Monitor.",
            "amount_zscore_by_account uses each account's full-window statistics (mild temporal lookahead in one engineered fraud feature).",
            "Card contextual features and the stablecoin domain are synthetic; stablecoin label is synthetic.",
            "Macro variables are used for stress overlays only; no individual-default causality is claimed.",
            "Loss figures are assumption-driven estimates, not realized losses.",
            "This is a research/portfolio build, not a deployed system; the stablecoin module uses AML-style risk indicators only.",
        ],
    }
    write_json(config.OUTPUTS / "methodology_summary.json", methodology)
    return methodology
