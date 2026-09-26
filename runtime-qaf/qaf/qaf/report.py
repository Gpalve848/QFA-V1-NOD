"""Console / CSV reporting of assessments and experiment summaries."""

from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

from .collector import QUERIES
from .engine import SystemAssessment

METRIC_COLUMNS = list(QUERIES) + ["tail_ratio"]


def _fmt(v, digits=1) -> str:
    return "-" if v is None else f"{v:.{digits}f}"


def format_assessment(a: SystemAssessment) -> str:
    dims = list(next(iter(a.services.values())).dimension_scores) if a.services else []
    ts = dt.datetime.fromtimestamp(a.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"Runtime Quality Assessment  @ {ts}",
        f"Weights ({a.weights.method}): " + ", ".join(f"{d}={w:.3f}" for d, w in a.weights.weights.items()),
    ]
    if "cr" in a.weights.details:
        lines.append(f"AHP consistency ratio: {a.weights.details['cr']:.3f}"
                     + ("  (consistent)" if a.weights.details.get("consistent") else "  (INCONSISTENT - revise matrix)"))
    lines.append("")

    header = f"{'service':<10}" + "".join(f"{d[:12]:>13}" for d in dims) + f"{'QI':>8}  {'level':<10}{'loss share':>10}"
    lines += [header, "-" * len(header)]
    for s, sa in a.services.items():
        lines.append(
            f"{s:<10}" + "".join(f"{_fmt(sa.dimension_scores[d]):>13}" for d in dims)
            + f"{_fmt(sa.quality_index):>8}  {sa.level:<10}{_fmt(a.contributions.get(s)) + '%':>10}"
        )
    lines += ["-" * len(header), f"SYSTEM QUALITY INDEX: {_fmt(a.system_quality_index)}  ({a.system_level})"]
    if a.bottleneck:
        lines.append(f"Largest contributor to quality loss: {a.bottleneck}")

    lines += ["", "Key metrics:",
              f"{'service':<10}{'p95 ms':>9}{'avg ms':>9}{'rps':>8}{'err %':>8}{'avail %':>9}{'cpu %':>8}{'mem %':>8}{'tail':>7}"]
    for s, sa in a.services.items():
        m = sa.metrics
        lines.append(
            f"{s:<10}{_fmt(m.get('latency_p95_ms')):>9}{_fmt(m.get('latency_avg_ms')):>9}{_fmt(m.get('throughput_rps')):>8}"
            f"{_fmt(m.get('error_rate_pct'), 2):>8}{_fmt(m.get('availability_pct')):>9}{_fmt(m.get('cpu_pct')):>8}"
            f"{_fmt(m.get('memory_pct')):>8}{_fmt(m.get('tail_ratio')):>7}"
        )

    recs = [(s, r) for s, sa in a.services.items() for r in sa.recommendations]
    lines += ["", "Recommendations:" if recs else "Recommendations: none - all services within thresholds."]
    for s, r in recs:
        lines.append(f"  [{r.severity.upper():<8}] {s:<8} {r.dimension:<12} {r.message}")
    return "\n".join(lines)


def assessment_rows(a: SystemAssessment, scenario: str = "") -> list[dict]:
    """One flat row per service, suitable for CSV and later statistical analysis."""
    iso = dt.datetime.fromtimestamp(a.timestamp).isoformat(timespec="seconds")
    rows = []
    for s, sa in a.services.items():
        row = {"timestamp": iso, "scenario": scenario, "service": s}
        row.update({m: sa.metrics.get(m) for m in METRIC_COLUMNS})
        row.update({f"dim_{d}": v for d, v in sa.dimension_scores.items()})
        row.update({
            "quality_index": sa.quality_index,
            "level": sa.level,
            "system_quality_index": a.system_quality_index,
            "system_level": a.system_level,
            "weight_method": a.weights.method,
        })
        rows.append(row)
    return rows


def append_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        if new:
            writer.writeheader()
        writer.writerows(rows)


def read_csv(paths: list[Path]) -> list[dict]:
    rows = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    return rows


def _mean(values) -> float | None:
    nums = [float(v) for v in values if v not in (None, "", "None")]
    return sum(nums) / len(nums) if nums else None


def summarize(rows: list[dict]) -> str:
    """Mean QI, dimension scores and key metrics per scenario and service."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    system: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[(r["scenario"], r["service"])].append(r)
        system[r["scenario"]].append(r["system_quality_index"])

    dim_cols = [c for c in rows[0] if c.startswith("dim_")] if rows else []
    header = (f"{'scenario':<24}{'service':<10}" + "".join(f"{c[4:][:11]:>12}" for c in dim_cols)
              + f"{'QI':>8}{'p95 ms':>9}{'err %':>8}{'cpu %':>8}{'n':>5}")
    lines = [header, "-" * len(header)]
    for (scenario, service), grp in sorted(groups.items()):
        lines.append(
            f"{scenario:<24}{service:<10}" + "".join(f"{_fmt(_mean(r[c] for r in grp)):>12}" for c in dim_cols)
            + f"{_fmt(_mean(r['quality_index'] for r in grp)):>8}{_fmt(_mean(r['latency_p95_ms'] for r in grp)):>9}"
            f"{_fmt(_mean(r['error_rate_pct'] for r in grp), 2):>8}{_fmt(_mean(r['cpu_pct'] for r in grp)):>8}{len(grp):>5}"
        )
    lines += ["", "System QI by scenario:"]
    for scenario, values in sorted(system.items()):
        lines.append(f"  {scenario:<24}{_fmt(_mean(values))}")
    return "\n".join(lines)
