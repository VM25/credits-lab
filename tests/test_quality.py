import pandas as pd
from src import config
from src.data import splits, quality


def test_time_split_no_overlap_and_ordered():
    s = splits.time_split(pd.DataFrame({"d": pd.date_range("2010-01-01", periods=100, freq="D")}), "d")
    assert s["train"].max() < s["val"].min() <= s["val"].max() < s["test"].min()


def test_quality_report_and_leakage_pass():
    rep = quality.run()
    need = {"dataset_name","row_count","column_count","missing_value_count",
            "duplicate_id_count","target_rate","date_min","date_max",
            "leakage_check_status","schema_check_status"}
    assert need.issubset(rep.columns)
    assert (rep["leakage_check_status"] == "pass").all()
    assert (config.OUTPUTS / "data_quality_report.csv").exists()
