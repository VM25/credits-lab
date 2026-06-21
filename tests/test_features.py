from src.data import features

LEAK = {"recoveries","collection_recovery_fee","total_pymnt","total_rec_prncp",
        "total_rec_int","last_pymnt_d","last_pymnt_amnt","out_prncp","next_pymnt_d","loan_status"}


def test_underwriting_features_present_no_leakage():
    uw, fr, val = features.run()
    for c in ["income_to_loan_ratio","debt_burden_score","credit_utilization_band",
              "loan_size_band","credit_grade_numeric","prior_delinquency_flag","application_vintage"]:
        assert c in uw.columns
    assert not (LEAK & set(uw.columns))
    assert uw["default_flag"].notna().all()
    # label-derived columns must not be in the feature lists
    assert "default_flag" not in features.UNDERWRITING_FEATURES
    assert "fraud_flag" not in features.FRAUD_FEATURES
    assert "chargeback_loss" not in features.FRAUD_FEATURES


def test_fraud_features_present():
    uw, fr, val = features.run()
    for c in ["velocity_1h","velocity_24h","amount_zscore_by_account","merchant_risk_score",
              "new_device_flag","new_location_flag","night_transaction_flag","high_amount_flag"]:
        assert c in fr.columns
