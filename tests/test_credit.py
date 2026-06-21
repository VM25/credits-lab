import pandas as pd
from src import config
from src.data import ingest_credit

LEAK = {"recoveries","collection_recovery_fee","total_pymnt","total_rec_prncp",
        "total_rec_int","last_pymnt_d","last_pymnt_amnt","out_prncp","next_pymnt_d","loan_status"}

def test_schema_target_and_no_leakage():
    df = ingest_credit.run()
    need = {"applicant_id","application_date","loan_amount","annual_income",
            "debt_to_income","employment_length","credit_grade","interest_rate",
            "loan_purpose","home_ownership","delinquency_history",
            "revolving_utilization","open_accounts","default_flag","loss_amount_if_default"}
    assert need.issubset(df.columns)
    assert set(df["default_flag"].dropna().unique()) <= {0,1}
    assert not (LEAK & set(df.columns))
    assert df["default_flag"].nunique() == 2

def test_sample_preserves_years_for_splits():
    df = ingest_credit.run()
    yrs = pd.to_datetime(df["application_date"], errors="coerce").dt.year.value_counts()
    assert (yrs >= 100).sum() >= 5
