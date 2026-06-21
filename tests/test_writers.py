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

import math
def test_write_json_nonfinite_becomes_null(tmp_path):
    p = tmp_path / "n.json"
    writers.write_json(p, {"a": float("nan"), "b": float("inf"), "c": 1.0})
    d = json.loads(p.read_text())   # would raise if NaN/Infinity emitted
    assert d["a"] is None and d["b"] is None and d["c"] == 1.0

import numpy as np
def test_write_json_rounds_in_tuples_and_numpy(tmp_path):
    p = tmp_path / "t.json"
    writers.write_json(p, {"bands": [("A", 0.0200001), ("B", np.float64(0.0500009))]})
    d = json.loads(p.read_text())
    assert d["bands"][0] == ["A", 0.02] and d["bands"][1][1] == 0.050001
