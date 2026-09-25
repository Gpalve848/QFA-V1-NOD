"""Command-line interface:  qaf assess | serve | record | summarize | weights | chaos"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import time
from pathlib import Path

import requests

from . import report
from .config import load_config
from .engine import assess
from .weighting import ahp_weights, entropy_weights, score_matrix

RESULTS_DIR = Path(__file__).resolve().parents[2] / "experiments" / "results"


def cmd_assess(args, cfg):
    a = assess(cfg)
    if args.json:
        print(json.dumps(a.to_dict(), indent=2, default=str))
    else:
        print(report.format_assessment(a))
    if args.save:
        Path(args.save).write_text(json.dumps(a.to_dict(), indent=2, default=str), encoding="utf-8")


def cmd_serve(args, cfg):
    from .exporter import serve
    serve(cfg, args.port, args.interval)


def cmd_record(args, cfg):
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else RESULTS_DIR / f"{args.scenario}_{stamp}.csv"
    end = time.time() + args.duration
    n = 0
    print(f"Recording scenario '{args.scenario}' for {args.duration}s every {args.interval}s -> {out}")
    while time.time() < end:
        try:
            a = assess(cfg)
            report.append_csv(out, report.assessment_rows(a, args.scenario))
            n += 1
            qi = a.system_quality_index
            print(f"  [{n:>3}] system QI = {'-' if qi is None else f'{qi:.1f}'} ({a.system_level})"
                  + (f", bottleneck: {a.bottleneck}" if a.bottleneck else ""))
        except Exception as exc:
            print(f"  assessment failed: {exc}")
        time.sleep(args.interval)
    if n:
        print()
        print(report.summarize(report.read_csv([out])))


def cmd_summarize(args, cfg):
    print(report.summarize(report.read_csv([Path(p) for p in args.files])))


def cmd_weights(args, cfg):
    dims = list(cfg["dimensions"])
    ahp = ahp_weights(cfg["weighting"]["ahp_matrix"])
    print("AHP weights:")
    for d, w in zip(dims, ahp.weights):
        print(f"  {d:<13}{w:.3f}")
    print(f"  lambda_max={ahp.lambda_max:.4f}  CI={ahp.ci:.4f}  CR={ahp.cr:.4f}  -> "
          + ("consistent (CR < 0.10)" if ahp.consistent else "INCONSISTENT (CR >= 0.10)"))
    if args.csv:
        rows = report.read_csv([Path(p) for p in args.csv])
        obs = [{d: (float(r[f"dim_{d}"]) if r.get(f"dim_{d}") not in (None, "", "None") else None) for d in dims} for r in rows]
        ent = entropy_weights(score_matrix(obs, dims))
        alpha = float(cfg["weighting"].get("hybrid_alpha", 0.5))
        print(f"\nEntropy weights from {len(obs)} recorded observations (and hybrid, alpha={alpha}):")
        for d, we, wa in zip(dims, ent, ahp.weights):
            print(f"  {d:<13}{we:.3f}   hybrid {alpha * wa + (1 - alpha) * we:.3f}")


def cmd_chaos(args, cfg):
    url = cfg["services"][args.service]["url"].rstrip("/") + "/chaos"
    if args.reset:
        resp = requests.delete(url, timeout=5)
    else:
        body = {k: v for k, v in {
            "latencyMs": args.latency, "errorRate": args.error_rate,
            "cpuBurnMs": args.cpu_burn, "leakMb": args.leak_mb,
        }.items() if v is not None}
        resp = requests.post(url, json=body, timeout=5)
    resp.raise_for_status()
    print(json.dumps(resp.json(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qaf", description="Runtime Quality Assessment Framework")
    p.add_argument("--config", help="path to qaf.yaml (default: bundled config)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("assess", help="run one assessment and print the report")
    s.add_argument("--json", action="store_true", help="print JSON instead of a table")
    s.add_argument("--save", help="also save the JSON result to this file")
    s.set_defaults(func=cmd_assess)

    s = sub.add_parser("serve", help="continuously assess and expose results as Prometheus metrics")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--interval", type=float, default=15)
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("record", help="record assessments for an experiment scenario to CSV")
    s.add_argument("--scenario", required=True, help="e.g. low, medium, peak, failure-payment")
    s.add_argument("--duration", type=int, default=300, help="seconds")
    s.add_argument("--interval", type=float, default=15, help="seconds between assessments")
    s.add_argument("--out", help="CSV path (default: experiments/results/<scenario>_<time>.csv)")
    s.set_defaults(func=cmd_record)

    s = sub.add_parser("summarize", help="summarise recorded CSV files per scenario and service")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=cmd_summarize)

    s = sub.add_parser("weights", help="show AHP weights / consistency and entropy weights from recordings")
    s.add_argument("--csv", nargs="*", help="recorded CSV files used for the entropy weight method")
    s.set_defaults(func=cmd_weights)

    s = sub.add_parser("chaos", help="inject or reset faults in a service")
    s.add_argument("service")
    s.add_argument("--latency", type=float, help="added latency in ms")
    s.add_argument("--error-rate", type=float, help="fraction of requests failing with 500 (0-1)")
    s.add_argument("--cpu-burn", type=float, help="busy-loop ms per request")
    s.add_argument("--leak-mb", type=int, help="allocate and hold this many MB")
    s.add_argument("--reset", action="store_true", help="remove all injected faults")
    s.set_defaults(func=cmd_chaos)
    return p


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    args.func(args, load_config(args.config))


if __name__ == "__main__":
    main()
