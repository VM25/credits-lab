from src import config
from src.data import ingest_stablecoin


def test_stablecoin_schema_and_ranges():
    df = ingest_stablecoin.run()
    need = {"wallet_id","counterparty_wallet_id","transaction_time","token_type",
            "amount_usd","wallet_age_days","inflow_24h","outflow_24h",
            "transaction_count_24h","counterparty_risk_score",
            "risky_address_exposure_flag","stablecoin_risk_label"}
    assert need.issubset(df.columns)
    assert (df["amount_usd"] > 0).all()
    assert df["counterparty_risk_score"].between(0, 1).all()
    assert set(df["stablecoin_risk_label"].unique()) <= {0, 1}
    assert set(df["risky_address_exposure_flag"].unique()) <= {0, 1}
    assert df["is_synthetic"].all()
    assert len(df) >= 2000
