import json

import pandas as pd

from src import config
from src.risk import stablecoin as sc


def test_stablecoin_outputs():
    sc.build()
    df = pd.read_csv(config.OUTPUTS / "stablecoin_alerts.csv")
    need = {"wallet_id", "counterparty_wallet_id", "transaction_time", "amount_usd",
            "stablecoin_risk_score", "stablecoin_risk_action", "risk_exposure_score",
            "top_reason_1", "top_reason_2", "top_reason_3"}
    assert need.issubset(df.columns)
    assert df["stablecoin_risk_score"].between(0, 1).all()
    assert (df["risk_exposure_score"] >= 0).all()
    assert set(df["stablecoin_risk_action"].unique()) <= {"normal", "monitor", "review", "high_risk"}
    j = json.load(open(config.OUTPUTS / "stablecoin_alerts.json"))
    for k in ["rows", "action_mix", "high_risk_wallet_count", "risk_exposure_by_action",
              "wallet_risk_leaderboard"]:
        assert k in j
    # no AML-compliance claim anywhere in the JSON
    assert "aml compliance" not in json.dumps(j).lower()
