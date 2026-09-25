"""Modules 3 & 4 - Quality Analyzer and Quality Index Calculator, plus classification."""

from __future__ import annotations


def normalize(value: float | None, good: float, bad: float) -> float | None:
    """Threshold-based min-max normalisation to a 0-100 score (100 = good).

    Works for both directions: if good < bad lower values are better, otherwise higher.
    """
    if value is None:
        return None
    if good == bad:
        return 100.0 if value == good else 0.0
    t = (value - bad) / (good - bad)
    return 100.0 * min(1.0, max(0.0, t))


def weighted_mean(scores: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Weighted mean over the entries that have a score; weights are renormalised
    over the available entries so missing data does not drag the result to zero."""
    available = {k: w for k, w in weights.items() if scores.get(k) is not None and w > 0}
    total = sum(available.values())
    if total == 0:
        return None
    return sum(scores[k] * w for k, w in available.items()) / total


def metric_scores(metrics: dict[str, float | None], cfg: dict) -> dict[str, float | None]:
    return {name: normalize(metrics.get(name), spec["good"], spec["bad"]) for name, spec in cfg["metrics"].items()}


def dimension_scores(m_scores: dict[str, float | None], cfg: dict) -> dict[str, float | None]:
    return {dim: weighted_mean(m_scores, sub_weights) for dim, sub_weights in cfg["dimensions"].items()}


def quality_index(d_scores: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """QI = sum(w_i * D_i) over available dimensions (weights renormalised)."""
    return weighted_mean(d_scores, weights)


def classify(qi: float | None, levels: dict[str, float]) -> str:
    if qi is None:
        return "Unknown"
    for label, lower in sorted(levels.items(), key=lambda kv: kv[1], reverse=True):
        if qi >= lower:
            return label
    return "Critical"


def degradation_contributions(service_qi: dict[str, float | None], service_weights: dict[str, float]) -> dict[str, float]:
    """Share (%) of the total system quality loss attributable to each service:
    contribution_s = w_s * (100 - QI_s) / sum_k w_k * (100 - QI_k)."""
    losses = {s: service_weights.get(s, 1.0) * (100.0 - qi) for s, qi in service_qi.items() if qi is not None}
    total = sum(losses.values())
    if total <= 0:
        return {s: 0.0 for s in losses}
    return {s: 100.0 * loss / total for s, loss in losses.items()}
