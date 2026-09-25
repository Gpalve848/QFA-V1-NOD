"""Exposes QAF results as Prometheus metrics so Grafana can chart the Quality Index."""

from __future__ import annotations

import logging
import time

from prometheus_client import Gauge, start_http_server

from .engine import SystemAssessment, assess

LEVEL_VALUE = {"Critical": 0, "Poor": 1, "Fair": 2, "Good": 3, "Excellent": 4}

SYSTEM_QI = Gauge("qaf_system_quality_index", "System-level runtime Quality Index (0-100)")
SERVICE_QI = Gauge("qaf_quality_index", "Service runtime Quality Index (0-100)", ["service"])
SERVICE_LEVEL = Gauge("qaf_quality_level", "Quality level: 0=Critical 1=Poor 2=Fair 3=Good 4=Excellent", ["service"])
DIMENSION = Gauge("qaf_dimension_score", "Quality dimension score (0-100)", ["service", "dimension"])
CONTRIBUTION = Gauge("qaf_degradation_contribution_pct", "Share of system quality loss caused by the service", ["service"])
WEIGHT = Gauge("qaf_dimension_weight", "Weight assigned to each quality dimension", ["dimension"])
RECOMMENDATIONS = Gauge("qaf_active_recommendations", "Number of active recommendations", ["service", "severity"])
LAST_RUN = Gauge("qaf_last_assessment_timestamp_seconds", "Unix time of the last successful assessment")

log = logging.getLogger("qaf.exporter")


def publish(a: SystemAssessment) -> None:
    for g in (SERVICE_QI, SERVICE_LEVEL, DIMENSION, CONTRIBUTION, WEIGHT, RECOMMENDATIONS):
        g.clear()
    if a.system_quality_index is not None:
        SYSTEM_QI.set(a.system_quality_index)
    for d, w in a.weights.weights.items():
        WEIGHT.labels(d).set(w)
    for s, sa in a.services.items():
        if sa.quality_index is not None:
            SERVICE_QI.labels(s).set(sa.quality_index)
            SERVICE_LEVEL.labels(s).set(LEVEL_VALUE.get(sa.level, 0))
        for d, v in sa.dimension_scores.items():
            if v is not None:
                DIMENSION.labels(s, d).set(v)
        for sev in ("warning", "critical"):
            RECOMMENDATIONS.labels(s, sev).set(sum(r.severity == sev for r in sa.recommendations))
    for s, c in a.contributions.items():
        CONTRIBUTION.labels(s).set(c)
    LAST_RUN.set(a.timestamp)


def serve(cfg: dict, port: int, interval: float) -> None:
    start_http_server(port)
    log.info("QAF exporter on :%d, assessing every %.0fs against %s", port, interval, cfg["prometheus_url"])
    while True:
        try:
            a = assess(cfg)
            publish(a)
            log.info("system QI=%s (%s)", None if a.system_quality_index is None else round(a.system_quality_index, 1), a.system_level)
        except Exception as exc:  # keep serving; Prometheus may not be ready yet
            log.warning("assessment failed: %s", exc)
        time.sleep(interval)
