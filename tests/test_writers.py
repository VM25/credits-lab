import json, pandas as pd
from src.reporting import writers

def test_write_json_sorted_and_rounded(tmp_path):
    p = tmp_path / "x.json"
    writers.write_json(p, {"b": 1.123456789, "a": 2})
    txt = p.read_text()
    assert txt.index('"a"') < txt.index('"b"')          # sorted keys
    assert json.loads(txt)["b"] == 1.123457              # rounded 6dp

def test_write_csv_rounds_floats(tmp_path):
    p = tmp_path / "x.csv"
    writers.write_csv(p, pd.DataFrame({"v": [1.123456789]}))
    assert "1.123457" in p.read_text()
