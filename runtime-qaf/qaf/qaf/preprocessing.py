"""Module 2 - Metric Preprocessing: noise removal, missing-data handling, aggregation."""

from __future__ import annotations

import math

import numpy as np


def clean_series(values, iqr_k: float = 1.5) -> list[float]:
    """Drops NaN/inf samples (missing data) and IQR outliers (noise)."""
    finite = [float(v) for v in values if v is not None and math.isfinite(v)]
    if len(finite) < 4:
        return finite
    q1, q3 = np.percentile(finite, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - iqr_k * iqr, q3 + iqr_k * iqr
    return [v for v in finite if lo <= v <= hi]


def aggregate(values: list[float], method: str = "median", alpha: float = 0.3) -> float | None:
    """Reduces a cleaned series to one representative value; None if no data."""
    if not values:
        return None
    if method == "mean":
        return float(np.mean(values))
    if method == "ewma":
        smoothed = values[0]
        for v in values[1:]:
            smoothed = alpha * v + (1 - alpha) * smoothed
        return float(smoothed)
    return float(np.median(values))


def is_down(up_series) -> bool:
    """True when the most recent health sample shows the service unreachable."""
    finite = [v for v in up_series if v is not None and math.isfinite(v)]
    return bool(finite) and finite[-1] == 0


def preprocess(raw: dict[str, dict[str, list[float]]], cfg: dict) -> dict[str, dict[str, float | None]]:
    """{service: {metric: samples}} -> {service: {metric: value or None}}, plus derived metrics."""
    pp = cfg.get("preprocessing", {})
    k = float(pp.get("outlier_iqr_k", 1.5))
    method = pp.get("aggregation", "median")
    alpha = float(pp.get("ewma_alpha", 0.3))

    result: dict[str, dict[str, float | None]] = {}
    for service, metrics in raw.items():
        values = {m: aggregate(clean_series(s, k), method, alpha) for m, s in metrics.items()}

        # A service that is down right now must not be scored on samples from before
        # the outage: keep only availability, so its QI collapses to the availability score.
        if is_down(metrics.get("up_pct", [])):
            values = {m: (v if m in ("availability_pct", "up_pct") else None) for m, v in values.items()}
            values["up_pct"] = 0.0

        # Derived metric for scalability: tail amplification under load.
        p50, p99 = values.get("latency_p50_ms"), values.get("latency_p99_ms")
        values["tail_ratio"] = p99 / p50 if p50 and p99 is not None and p50 > 0 else None

        result[service] = values
    return result
