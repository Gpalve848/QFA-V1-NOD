import math

import numpy as np
import pytest

from qaf import scoring
from qaf.config import load_config
from qaf.engine import assess_metrics
from qaf.preprocessing import aggregate, clean_series, preprocess
from qaf.weighting import ahp_weights, entropy_weights, resolve_weights


@pytest.fixture
def cfg():
    return load_config()


HEALTHY = {
    "latency_p50_ms": 20, "latency_p95_ms": 60, "latency_p99_ms": 80, "latency_avg_ms": 25,
    "throughput_rps": 30, "error_rate_pct": 0.0, "availability_pct": 100, "cpu_pct": 20,
    "memory_pct": 30, "tail_ratio": 4.0,
}


def test_normalize_lower_is_better():
    assert scoring.normalize(100, good=100, bad=1000) == 100
    assert scoring.normalize(1000, good=100, bad=1000) == 0
    assert scoring.normalize(550, good=100, bad=1000) == pytest.approx(50)
    assert scoring.normalize(5000, good=100, bad=1000) == 0


def test_normalize_higher_is_better():
    assert scoring.normalize(100, good=100, bad=95) == 100
    assert scoring.normalize(97.5, good=100, bad=95) == pytest.approx(50)
    assert scoring.normalize(None, good=100, bad=95) is None


def test_weighted_mean_ignores_missing():
    assert scoring.weighted_mean({"a": 80, "b": None}, {"a": 0.5, "b": 0.5}) == 80
    assert scoring.weighted_mean({"a": None}, {"a": 1}) is None


def test_classify_bands(cfg):
    levels = cfg["quality_levels"]
    assert scoring.classify(95, levels) == "Excellent"
    assert scoring.classify(75, levels) == "Good"
    assert scoring.classify(60, levels) == "Fair"
    assert scoring.classify(45, levels) == "Poor"
    assert scoring.classify(10, levels) == "Critical"


def test_ahp_default_matrix_is_consistent(cfg):
    res = ahp_weights(cfg["weighting"]["ahp_matrix"])
    assert res.consistent
    assert res.weights.sum() == pytest.approx(1)
    assert res.weights[0] == max(res.weights)  # performance ranked most important


def test_ahp_detects_inconsistency():
    bad = [[1, 9, 1 / 9], [1 / 9, 1, 9], [9, 1 / 9, 1]]
    assert not ahp_weights(bad).consistent


def test_entropy_prefers_discriminating_criteria():
    x = np.array([[100, 10], [100, 90], [100, 50]])
    w = entropy_weights(x)
    assert w[1] > w[0]
    assert w.sum() == pytest.approx(1)


def test_clean_series_removes_outliers_and_nan():
    cleaned = clean_series([10, 11, 9, 10, 12, 500, math.nan])
    assert 500 not in cleaned and len(cleaned) == 5
    assert aggregate(cleaned, "median") == 10


def test_preprocess_derives_tail_ratio(cfg):
    out = preprocess({"s": {"latency_p50_ms": [10, 10], "latency_p99_ms": [50, 50]}}, cfg)
    assert out["s"]["tail_ratio"] == pytest.approx(5)


def test_healthy_service_is_excellent(cfg):
    a = assess_metrics({"svc": HEALTHY}, cfg)
    assert a.services["svc"].level == "Excellent"
    assert a.services["svc"].recommendations == []


def test_degraded_service_is_detected_and_blamed(cfg):
    degraded = {**HEALTHY, "latency_p95_ms": 1500, "latency_avg_ms": 600, "error_rate_pct": 8, "cpu_pct": 97}
    a = assess_metrics({"order": degraded, "user": HEALTHY}, cfg)
    assert a.services["order"].quality_index < 50
    assert a.bottleneck == "order"
    dims = {r.dimension for r in a.services["order"].recommendations}
    assert {"performance", "reliability", "efficiency"} <= dims


def test_down_service_scores_zero(cfg):
    down = {k: None for k in HEALTHY} | {"availability_pct": 0.0}
    a = assess_metrics({"payment": down}, cfg)
    assert a.services["payment"].quality_index == 0
    assert a.services["payment"].level == "Critical"


@pytest.mark.parametrize("method", ["fixed", "ahp", "entropy", "hybrid"])
def test_all_weighting_methods_sum_to_one(cfg, method):
    cfg["weighting"]["method"] = method
    obs = [{"performance": 90, "reliability": 100, "availability": 100, "efficiency": 70, "scalability": 80},
           {"performance": 40, "reliability": 60, "availability": 100, "efficiency": 90, "scalability": 50}]
    w = resolve_weights(cfg, obs).weights
    assert sum(w.values()) == pytest.approx(1)
