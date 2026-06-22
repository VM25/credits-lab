import json
import pandas as pd
from src import config
from src.validation import validate


def test_validation_outputs():
    validate.build()
    for f in ["credit_model_validation.csv", "fraud_model_validation.csv", "stablecoin_model_validation.csv"]:
        assert (config.OUTPUTS / f).exists()
    summ = json.load(open(config.OUTPUTS / "model_validation_summary.json"))
    # calibration curve + decile table are EMBEDDED here (not separate files)
    assert "calibration_curve" in summ and "decile_default_table" in summ
    assert not (config.OUTPUTS / "calibration_curve.json").exists()
    assert not (config.OUTPUTS / "decile_default_table.csv").exists()
    cc = json.load(open(config.OUTPUTS / "champion_challenger_comparison.json"))
    assert "recommendation" in cc
    verdicts = json.load(open(config.OUTPUTS / "model_risk_verdicts.json"))
    vlist = verdicts if isinstance(verdicts, list) else verdicts.get("verdicts", verdicts)
    assert len(vlist) == 5
    for v in vlist:
        assert v["validation_verdict"] in {"Pass", "Monitor", "Fail"}
        assert isinstance(v.get("verdict_reason", ""), str) and len(v["verdict_reason"]) > 0
    # decile default table should be roughly monotonic in actual default rate
    dt = summ["decile_default_table"]
    rates = [r["actual_default_rate"] for r in dt]
    assert rates[-1] > rates[0]


def test_no_aml_compliance_language():
    summ = json.load(open(config.OUTPUTS / "model_validation_summary.json"))
    assert "aml compliance" not in json.dumps(summ).lower()
