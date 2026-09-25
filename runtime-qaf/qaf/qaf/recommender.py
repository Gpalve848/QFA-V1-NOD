"""Module 5 - Recommendation Engine: rule-based mapping from quality issues to actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Recommendation:
    dimension: str
    severity: str  # warning | critical
    message: str


def _v(metrics: dict, key: str) -> float | None:
    return metrics.get(key)


def recommend(metrics: dict[str, float | None], d_scores: dict[str, float | None]) -> list[Recommendation]:
    recs: list[Recommendation] = []

    availability = _v(metrics, "availability_pct")
    if availability is not None and availability < 99.0:
        sev = "critical" if availability < 95 else "warning"
        recs.append(Recommendation("availability", sev,
            f"Availability {availability:.1f}%: service instances are going down. Check crash logs, "
            "add liveness/readiness probes and run more than one replica."))

    error_rate = _v(metrics, "error_rate_pct")
    if error_rate is not None and error_rate > 1.0:
        sev = "critical" if error_rate > 5 else "warning"
        recs.append(Recommendation("reliability", sev,
            f"Error rate {error_rate:.1f}%: investigate failing dependencies; add a circuit breaker, "
            "timeouts and retries with back-off."))

    p95 = _v(metrics, "latency_p95_ms")
    if p95 is not None and p95 > 500:
        sev = "critical" if p95 > 1000 else "warning"
        recs.append(Recommendation("performance", sev,
            f"p95 latency {p95:.0f} ms: add caching for hot reads, optimise slow queries/indexes and "
            "check downstream call latency."))

    cpu = _v(metrics, "cpu_pct")
    if cpu is not None and cpu > 80:
        sev = "critical" if cpu > 95 else "warning"
        recs.append(Recommendation("efficiency", sev,
            f"CPU at {cpu:.0f}% of limit: scale out (Horizontal Pod Autoscaler / more replicas) or raise "
            "the CPU limit; profile hot code paths."))

    mem = _v(metrics, "memory_pct")
    if mem is not None and mem > 80:
        sev = "critical" if mem > 95 else "warning"
        recs.append(Recommendation("efficiency", sev,
            f"Memory at {mem:.0f}% of limit: risk of OOM kill. Check for memory leaks, unbounded caches, "
            "or raise the memory limit."))

    tail = _v(metrics, "tail_ratio")
    if tail is not None and tail > 10:
        recs.append(Recommendation("scalability", "warning",
            f"Tail latency is {tail:.1f}x the median: requests are queueing (saturation). Scale out and "
            "review thread/connection pool sizes."))

    if not recs:
        weakest = min(((d, s) for d, s in d_scores.items() if s is not None), key=lambda x: x[1], default=None)
        if weakest and weakest[1] < 75:
            recs.append(Recommendation(weakest[0], "warning",
                f"Weakest dimension is {weakest[0]} ({weakest[1]:.0f}/100); monitor for further degradation."))
    return recs
