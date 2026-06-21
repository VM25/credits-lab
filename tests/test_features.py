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
    # stateless predictor lists are non-empty and exclude label-derived columns
    uwf = features.underwriting_features(uw)
    assert len(uwf) > 0
    assert "default_flag" not in uwf
    assert "loss_amount_if_default" not in uwf
    assert not (LEAK & set(uwf))


def test_fraud_features_present_no_label_leakage():
    uw, fr, val = features.run()
    for c in ["velocity_1h","velocity_24h","amount_zscore_by_account","merchant_risk_score",
              "new_device_flag","new_location_flag","night_transaction_flag","high_amount_flag"]:
        assert c in fr.columns
    frf = features.fraud_features(fr)
    assert len(frf) > 0
    assert "fraud_flag" not in frf
    assert "chargeback_loss" not in frf
    # real PCA features are retained as predictors
    assert sum(c == f"V{i}" for i in range(1, 29) for c in frf) == 28
