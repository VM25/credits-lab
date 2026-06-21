import numpy as np
from src.models import metrics, calibration, scorecard, gbm

def test_metrics_ranges():
    y = np.array([0,0,1,1,0,1]); s = np.array([.1,.2,.8,.7,.3,.9])
    assert 0 <= metrics.roc_auc(y,s) <= 1
    assert 0 <= metrics.pr_auc(y,s) <= 1
    assert 0 <= metrics.brier(y,s) <= 1
    assert 0 <= metrics.ks(y,s) <= 1
    conf = metrics.confusion_at(y, s, 0.5)
    assert set(conf) == {"tp","fp","tn","fn"} and sum(conf.values()) == len(y)

def test_psi_status_bands():
    assert metrics.psi_status(0.05) == "stable"
    assert metrics.psi_status(0.15) == "monitor"
    assert metrics.psi_status(0.30) == "material"

def test_calibration_outputs_probabilities():
    y = np.random.RandomState(0).randint(0,2,500); s = np.random.RandomState(1).rand(500)
    cal = calibration.fit(s, y); p = cal.transform(s)
    assert ((p>=0)&(p<=1)).all()
    assert 0 <= cal.brier_after <= 1 and 0 <= cal.brier_before <= 1
    assert len(cal.curve) > 0

def test_models_fit_predict():
    rng = np.random.RandomState(0)
    X = rng.rand(300, 4); y = (X[:,0] + rng.rand(300) > 1.0).astype(int)
    sm = scorecard.fit(X, y, feature_names=["a","b","c","d"])
    gm = gbm.fit(X, y, feature_names=["a","b","c","d"])
    for m in (sm, gm):
        p = m.predict_proba(X)
        assert p.shape == (300,) and ((p>=0)&(p<=1)).all()
    assert set(sm.coefficients) == {"a","b","c","d"}
    assert set(gm.feature_importances) == {"a","b","c","d"}
