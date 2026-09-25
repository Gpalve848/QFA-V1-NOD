"""Configuration loading."""

from __future__ import annotations

import os
from fractions import Fraction
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "qaf.yaml"


def _to_number(value):
    """Allows AHP entries such as '1/3' in YAML."""
    if isinstance(value, str):
        return float(Fraction(value.strip()))
    return float(value)


def load_config(path: str | os.PathLike | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    if os.environ.get("QAF_PROMETHEUS_URL"):
        cfg["prometheus_url"] = os.environ["QAF_PROMETHEUS_URL"]

    weighting = cfg.setdefault("weighting", {})
    if "ahp_matrix" in weighting:
        weighting["ahp_matrix"] = [[_to_number(v) for v in row] for row in weighting["ahp_matrix"]]
    return cfg
