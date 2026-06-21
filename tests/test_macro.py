import pandas as pd
from src import config
from src.data import ingest_macro

def test_macro_schema_and_inflation():
    df = ingest_macro.run()
    need = {"date","unemployment_rate","policy_rate","inflation_rate",
            "consumer_credit_delinquency_rate","credit_card_chargeoff_rate"}
    assert need.issubset(df.columns)
    assert (config.PROCESSED / "macro_stress_inputs.csv").exists()
    assert df["inflation_rate"].notna().sum() > 0
    assert len(df) > 24
