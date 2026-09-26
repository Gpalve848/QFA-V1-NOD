"""Builds the figures and the results summary used in the mid-semester report.

    python docs/mid-sem-report/make_figures.py

Reads experiments/results/E*.csv and writes figures/*.png and results_summary.json.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "qaf"))
from qaf.config import load_config  # noqa: E402
from qaf.weighting import ahp_weights  # noqa: E402

OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

SERVICES = ["user", "product", "order", "payment"]
DIMENSIONS = ["performance", "reliability", "availability", "efficiency", "scalability"]
SCENARIO_LABELS = {
    "E1": "E1 Low", "E2": "E2 Medium", "E3": "E3 Peak", "E4": "E4 Spike",
    "E5": "E5 Payment errors", "E6": "E6 Order latency", "E7": "E7 Product CPU",
    "E8": "E8 User memory", "E9": "E9 Payment outage",
}
SERVICE_COLORS = {"user": "#4C72B0", "product": "#55A868", "order": "#C44E52", "payment": "#8172B2"}
LEVEL_BANDS = [(90, 100, "#d9f2d9", "Excellent"), (75, 90, "#fff4c2", "Good"), (60, 75, "#ffe0b3", "Fair"),
               (40, 60, "#ffc9c9", "Poor"), (0, 40, "#f2a6a6", "Critical")]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def num(v):
    return None if v in (None, "", "None") else float(v)


def mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def load_results():
    runs = {}
    for path in sorted((ROOT / "experiments" / "results").glob("E*.csv")):
        exp_id = path.stem.split("-")[0]
        with open(path, encoding="utf-8") as fh:
            runs[exp_id] = list(csv.DictReader(fh))
    return runs


def summarize(runs):
    summary = {}
    for exp_id, rows in runs.items():
        by_service = defaultdict(list)
        for r in rows:
            by_service[r["service"]].append(r)
        services = {}
        for s, grp in by_service.items():
            services[s] = {
                "qi": mean(num(r["quality_index"]) for r in grp),
                "dimensions": {d: mean(num(r[f"dim_{d}"]) for r in grp) for d in DIMENSIONS},
                "p95_ms": mean(num(r["latency_p95_ms"]) for r in grp),
                "error_pct": mean(num(r["error_rate_pct"]) for r in grp),
                "cpu_pct": mean(num(r["cpu_pct"]) for r in grp),
                "memory_pct": mean(num(r["memory_pct"]) for r in grp),
                "rps": mean(num(r["throughput_rps"]) for r in grp),
                "availability_pct": mean(num(r["availability_pct"]) for r in grp),
            }
        system_by_ts = {r["timestamp"]: num(r["system_quality_index"]) for r in rows}
        summary[exp_id] = {
            "scenario": rows[0]["scenario"],
            "label": SCENARIO_LABELS.get(exp_id, exp_id),
            "system_qi": mean(system_by_ts.values()),
            "samples": len(system_by_ts),
            "services": services,
        }
    return summary


def box(ax, x, y, w, h, text, color, fontsize=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=color, edgecolor="#333333", linewidth=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color="#333333", linewidth=1))
    if text:
        ax.text((x1 + x2) / 2 + 0.1, (y1 + y2) / 2, text, fontsize=8, va="center", color="#444444")


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10, 7.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    box(ax, 0.3, 8.9, 3.4, 0.8, "k6 load generator\nlow / medium / peak / spike", "#e8eef7")
    box(ax, 6.3, 8.9, 3.4, 0.8, "Fault injection (/chaos)\nlatency, errors, CPU, memory", "#f7e8e8")

    ax.add_patch(FancyBboxPatch((0.3, 6.5), 9.4, 1.9, boxstyle="round,pad=0.02,rounding_size=0.1",
                                facecolor="#f4f4f4", edgecolor="#777777", linestyle="--"))
    ax.text(0.5, 8.15, "Demo microservices (Node.js, Docker, 0.5 CPU / 256 MB each)", fontsize=9, fontweight="bold")
    for i, (name, port) in enumerate([("User", 3001), ("Product", 3002), ("Order", 3003), ("Payment", 3004)]):
        box(ax, 0.6 + i * 2.3, 6.75, 1.9, 1.0, f"{name} service\n:{port}  /metrics", "#ffffff")
    arrow(ax, 2.0, 8.9, 2.0, 8.4)
    arrow(ax, 8.0, 8.9, 8.0, 8.4)

    box(ax, 3.3, 5.1, 3.4, 0.8, "Prometheus  (scrape every 5 s)", "#fdebd0", bold=True)
    arrow(ax, 5.0, 6.5, 5.0, 5.9, "metrics")

    ax.add_patch(FancyBboxPatch((0.3, 0.9), 9.4, 3.6, boxstyle="round,pad=0.02,rounding_size=0.1",
                                facecolor="#eaf5ea", edgecolor="#2e7d32", linewidth=1.2))
    ax.text(0.5, 4.2, "Runtime Quality Assessment Framework (Python)", fontsize=10, fontweight="bold", color="#1b5e20")
    modules = ["M1\nMetric\nCollector", "M2\nPreprocessing\n(noise, gaps)", "M3\nQuality\nAnalyzer",
               "Weights\nAHP / Entropy", "M4\nQuality Index\n+ Classification", "M5\nRecommendation\nEngine"]
    for i, m in enumerate(modules):
        box(ax, 0.5 + i * 1.53, 2.3, 1.35, 1.5, m, "#ffffff", fontsize=8)
        if i:
            arrow(ax, 0.5 + i * 1.53 - 0.18, 3.05, 0.5 + i * 1.53, 3.05)
    arrow(ax, 5.0, 5.1, 5.0, 4.5, "PromQL query_range")

    box(ax, 0.6, 1.1, 2.8, 0.8, "Console report / CSV\n(qaf assess, qaf record)", "#ffffff", fontsize=8)
    box(ax, 3.7, 1.1, 2.6, 0.8, "Exporter :8000\nqaf_* metrics", "#ffffff", fontsize=8)
    box(ax, 6.6, 1.1, 2.9, 0.8, "Grafana dashboard :3000\nQI, levels, dimensions", "#ffffff", fontsize=8)
    for x in (2.0, 5.0, 8.05):
        arrow(ax, x, 2.3, x, 1.9)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_architecture.png", dpi=200)
    plt.close(fig)


def fig_ahp(cfg):
    res = ahp_weights(cfg["weighting"]["ahp_matrix"])
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.bar([d.capitalize() for d in DIMENSIONS], res.weights, color="#4C72B0")
    for b, w in zip(bars, res.weights):
        ax.text(b.get_x() + b.get_width() / 2, w + 0.005, f"{w:.3f}", ha="center", fontsize=9)
    ax.set_ylabel("Weight")
    ax.set_ylim(0, 0.36)
    ax.set_title(f"AHP dimension weights  (λmax = {res.lambda_max:.3f}, CR = {res.cr:.3f})", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_ahp_weights.png", dpi=200)
    plt.close(fig)
    return res


def shade_levels(ax, horizontal=False):
    for lo, hi, color, label in LEVEL_BANDS:
        (ax.axvspan if horizontal else ax.axhspan)(lo, hi, color=color, alpha=0.6, zorder=0)


def fig_system_qi(summary):
    ids = list(summary)
    labels = [summary[i]["label"] for i in ids]
    values = [summary[i]["system_qi"] for i in ids]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    shade_levels(ax, horizontal=True)
    bars = ax.barh(labels[::-1], values[::-1], color="#37474f", zorder=2)
    for b, v in zip(bars, values[::-1]):
        ax.text(v + 0.8, b.get_y() + b.get_height() / 2, f"{v:.1f}", va="center", fontsize=9, zorder=3)
    ax.set_xlim(0, 105)
    ax.set_xlabel("System Quality Index (mean over the recording window)")
    for lo, hi, _, label in LEVEL_BANDS:
        ax.text((lo + hi) / 2, len(ids) - 0.35, label, ha="center", fontsize=7.5, color="#555555")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_system_qi.png", dpi=200)
    plt.close(fig)


def fig_heatmap(summary):
    ids = list(summary)
    data = [[summary[i]["services"].get(s, {}).get("qi") or 0 for s in SERVICES] for i in ids]
    fig, ax = plt.subplots(figsize=(6.5, 5))
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(SERVICES)), [s.capitalize() for s in SERVICES])
    ax.set_yticks(range(len(ids)), [summary[i]["label"] for i in ids])
    for r, row in enumerate(data):
        for c, v in enumerate(row):
            ax.text(c, r, f"{v:.1f}", ha="center", va="center", fontsize=9, color="black" if v > 35 else "white")
    ax.spines[:].set_visible(False)
    fig.colorbar(im, ax=ax, label="Service QI")
    fig.tight_layout()
    fig.savefig(OUT / "fig4_service_qi_heatmap.png", dpi=200)
    plt.close(fig)


def fig_timelines(runs):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for ax, exp_id in zip(axes, ["E3", "E5", "E9"]):
        rows = runs[exp_id]
        shade_levels(ax)
        timestamps = sorted({r["timestamp"] for r in rows})
        t0 = timestamps[0]
        x = [(i) * 15 for i in range(len(timestamps))]
        for s in SERVICES:
            by_ts = {r["timestamp"]: num(r["quality_index"]) for r in rows if r["service"] == s}
            ax.plot(x, [by_ts.get(t) for t in timestamps], marker="o", markersize=3, label=s.capitalize(),
                    color=SERVICE_COLORS[s], zorder=3)
        sys_by_ts = {r["timestamp"]: num(r["system_quality_index"]) for r in rows}
        ax.plot(x, [sys_by_ts[t] for t in timestamps], color="black", linestyle="--", linewidth=1.6, label="System", zorder=4)
        ax.set_title(SCENARIO_LABELS[exp_id], fontsize=10)
        ax.set_xlabel(f"Seconds since recording start ({t0[11:16]})")
        ax.set_ylim(-3, 103)
    axes[0].set_ylabel("Quality Index")
    axes[-1].legend(loc="center right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_qi_timelines.png", dpi=200)
    plt.close(fig)


def fig_dimensions(summary):
    cases = [("E1", "order", "Order – E1 Low"), ("E3", "order", "Order – E3 Peak"),
             ("E6", "order", "Order – E6 Latency"), ("E7", "product", "Product – E7 CPU"),
             ("E8", "user", "User – E8 Memory")]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    width = 0.16
    colors = ["#4C72B0", "#C44E52", "#8172B2", "#55A868", "#CCB974"]
    for k, (exp_id, svc, label) in enumerate(cases):
        dims = summary[exp_id]["services"][svc]["dimensions"]
        vals = [dims[d] or 0 for d in DIMENSIONS]
        ax.bar([i + (k - 2) * width for i in range(len(DIMENSIONS))], vals, width, label=label, color=colors[k])
    ax.set_xticks(range(len(DIMENSIONS)), [d.capitalize() for d in DIMENSIONS])
    ax.set_ylabel("Dimension score")
    ax.set_ylim(0, 110)
    ax.legend(fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.15), frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "fig6_dimension_scores.png", dpi=200)
    plt.close(fig)


def main():
    cfg = load_config()
    runs = load_results()
    summary = summarize(runs)
    fig_architecture()
    ahp = fig_ahp(cfg)
    fig_system_qi(summary)
    fig_heatmap(summary)
    fig_timelines(runs)
    fig_dimensions(summary)
    out = {"ahp": {"weights": dict(zip(DIMENSIONS, map(float, ahp.weights))), "lambda_max": ahp.lambda_max,
                   "ci": ahp.ci, "cr": ahp.cr, "matrix": cfg["weighting"]["ahp_matrix"]},
           "experiments": summary}
    (HERE / "results_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("figures:", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
