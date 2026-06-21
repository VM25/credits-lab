from src import config

def test_thresholds_ordered_and_in_range():
    assert 0 < config.PD_APPROVE < config.PD_DECLINE < 1
    assert config.PD_APPROVE == 0.15 and config.PD_DECLINE == 0.30
    assert config.DOC_REFERENCE_PD_THRESHOLDS["approve"] == 0.06 and config.DOC_REFERENCE_PD_THRESHOLDS["decline"] == 0.12
    f = config.FRAUD_THRESHOLDS
    assert f["approve"] < f["stepup"] < f["review"] < f["block"]
    s = config.STABLECOIN_THRESHOLDS
    assert s["monitor"] < s["review"] < s["high_risk"]

def test_assumptions_present():
    assert config.LGD_DEFAULT == 0.55
    assert set(config.LGD_BY_RISK) >= {"low", "standard", "high"}
    assert config.UTILIZATION_ASSUMPTION == 0.65
    assert config.FRAUD_LOSS_SEVERITY == 0.90
    assert config.STRESS["severe"]["pd_mult"] == 1.60
    assert config.SEED == 20260620
