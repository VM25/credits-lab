import pandas as pd
from src import config
from src.data import ingest_payments

def test_real_labels_and_synthetic_context():
    df = ingest_payments.run()
    need = {"transaction_id","account_id","transaction_time","amount",
            "merchant_category","merchant_risk_band","location_proxy","device_proxy",
            "account_age_days","transaction_count_24h","amount_count_24h",
            "fraud_flag","chargeback_loss"}
    assert need.issubset(df.columns)
    assert set(df["fraud_flag"].unique()) <= {0,1}
    assert df["fraud_flag"].mean() < 0.02            # real imbalance preserved
    assert df["fraud_flag"].sum() == 492             # all real fraud cases kept
    assert any(c.startswith("V") for c in df.columns)
    assert df["is_synthetic_context"].all()
