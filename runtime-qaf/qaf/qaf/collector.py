"""Module 1 - Metric Collector: pulls runtime metrics from Prometheus."""

from __future__ import annotations

import math
import time

import requests

# PromQL templates, one per raw metric, each returning one series per `service` label.
QUERIES = {
    "latency_p50_ms": (
        "1000 * histogram_quantile(0.50, sum by (service, le) "
        '(rate(http_request_duration_seconds_bucket{{job="{job}"}}[{w}])))'
    ),
    "latency_p95_ms": (
        "1000 * histogram_quantile(0.95, sum by (service, le) "
        '(rate(http_request_duration_seconds_bucket{{job="{job}"}}[{w}])))'
    ),
    "latency_p99_ms": (
        "1000 * histogram_quantile(0.99, sum by (service, le) "
        '(rate(http_request_duration_seconds_bucket{{job="{job}"}}[{w}])))'
    ),
    "latency_avg_ms": (
        '1000 * sum by (service) (rate(http_request_duration_seconds_sum{{job="{job}"}}[{w}])) '
        '/ sum by (service) (rate(http_request_duration_seconds_count{{job="{job}"}}[{w}]))'
    ),
    "throughput_rps": 'sum by (service) (rate(http_requests_total{{job="{job}"}}[{w}]))',
    # `or ... * 0` turns "no 5xx series" into an explicit 0 % error rate.
    "error_rate_pct": (
        '100 * (sum by (service) (rate(http_requests_total{{job="{job}",status=~"5.."}}[{w}])) '
        'or sum by (service) (rate(http_requests_total{{job="{job}"}}[{w}])) * 0) '
        '/ sum by (service) (rate(http_requests_total{{job="{job}"}}[{w}]))'
    ),
    "availability_pct": '100 * avg by (service) (avg_over_time(up{{job="{job}"}}[{w}]))',
    "cpu_pct": '100 * sum by (service) (rate(process_cpu_seconds_total{{job="{job}"}}[{w}])) / {cpu}',
    "memory_pct": '100 * sum by (service) (process_resident_memory_bytes{{job="{job}"}}) / {mem}',
}


class PrometheusCollector:
    def __init__(self, cfg: dict, timeout: float = 10.0):
        self.url = cfg["prometheus_url"].rstrip("/")
        self.job = cfg.get("job", "microservices")
        col = cfg.get("collection", {})
        self.window = col.get("rate_window", "1m")
        self.lookback = int(col.get("lookback_seconds", 120))
        self.step = int(col.get("step_seconds", 10))
        res = cfg.get("resources", {})
        self.cpu_limit = float(res.get("cpu_limit_cores", 1.0))
        self.mem_limit_bytes = float(res.get("memory_limit_mb", 512)) * 1024 * 1024
        self.services = list(cfg.get("services", {}))
        self.timeout = timeout

    def promql(self, metric: str) -> str:
        return QUERIES[metric].format(job=self.job, w=self.window, cpu=self.cpu_limit, mem=self.mem_limit_bytes)

    def query_range(self, promql: str, start: float, end: float) -> dict[str, list[float]]:
        resp = requests.get(
            f"{self.url}/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": self.step},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {payload}")

        series: dict[str, list[float]] = {}
        for result in payload["data"]["result"]:
            service = result["metric"].get("service")
            if service is None:
                continue
            series[service] = [float(v) for _, v in result["values"]]
        return series

    def collect(self, end: float | None = None) -> dict[str, dict[str, list[float]]]:
        """Returns {service: {metric: [samples over the lookback window]}}."""
        end = end or time.time()
        start = end - self.lookback
        raw: dict[str, dict[str, list[float]]] = {s: {} for s in self.services}
        for metric in QUERIES:
            for service, values in self.query_range(self.promql(metric), start, end).items():
                raw.setdefault(service, {})[metric] = values
        # Every configured service gets every metric key, even when Prometheus has no data.
        for service in raw:
            for metric in QUERIES:
                raw[service].setdefault(metric, [math.nan])
        return raw
