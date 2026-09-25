"""Quality Assessment pipeline: collect -> preprocess -> score -> weight -> QI -> classify -> recommend."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from . import scoring
from .collector import PrometheusCollector
from .preprocessing import preprocess
from .recommender import Recommendation, recommend
from .weighting import WeightResult, resolve_weights


@dataclass
class ServiceAssessment:
    service: str
    metrics: dict[str, float | None]
    metric_scores: dict[str, float | None]
    dimension_scores: dict[str, float | None]
    quality_index: float | None
    level: str
    recommendations: list[Recommendation] = field(default_factory=list)


@dataclass
class SystemAssessment:
    timestamp: float
    weights: WeightResult
    services: dict[str, ServiceAssessment]
    system_quality_index: float | None
    system_level: str
    contributions: dict[str, float]

    @property
    def bottleneck(self) -> str | None:
        if not self.contributions or max(self.contributions.values()) == 0:
            return None
        return max(self.contributions, key=self.contributions.get)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["bottleneck"] = self.bottleneck
        return d


def assess_metrics(metrics_by_service: dict[str, dict[str, float | None]], cfg: dict, timestamp: float | None = None) -> SystemAssessment:
    """Runs the scoring pipeline on already-preprocessed metrics (no Prometheus needed)."""
    m_scores = {s: scoring.metric_scores(m, cfg) for s, m in metrics_by_service.items()}
    d_scores = {s: scoring.dimension_scores(ms, cfg) for s, ms in m_scores.items()}

    weights = resolve_weights(cfg, observations=list(d_scores.values()))
    levels = cfg["quality_levels"]

    services: dict[str, ServiceAssessment] = {}
    for s, metrics in metrics_by_service.items():
        qi = scoring.quality_index(d_scores[s], weights.weights)
        services[s] = ServiceAssessment(
            service=s,
            metrics=metrics,
            metric_scores=m_scores[s],
            dimension_scores=d_scores[s],
            quality_index=qi,
            level=scoring.classify(qi, levels),
            recommendations=recommend(metrics, d_scores[s]),
        )

    svc_cfg = cfg.get("services", {})
    service_weights = {s: float((svc_cfg.get(s) or {}).get("weight", 1.0)) for s in services}
    service_qi = {s: a.quality_index for s, a in services.items()}
    system_qi = scoring.weighted_mean(service_qi, service_weights)

    return SystemAssessment(
        timestamp=timestamp or time.time(),
        weights=weights,
        services=services,
        system_quality_index=system_qi,
        system_level=scoring.classify(system_qi, levels),
        contributions=scoring.degradation_contributions(service_qi, service_weights),
    )


def assess(cfg: dict, collector: PrometheusCollector | None = None) -> SystemAssessment:
    collector = collector or PrometheusCollector(cfg)
    now = time.time()
    raw = collector.collect(end=now)
    return assess_metrics(preprocess(raw, cfg), cfg, timestamp=now)
