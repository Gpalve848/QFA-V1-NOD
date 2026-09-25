"""Weight assignment: fixed, AHP (subjective), Entropy Weight Method (objective), hybrid."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Saaty's random consistency index for matrices of size n.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


@dataclass
class AhpResult:
    weights: np.ndarray
    lambda_max: float
    ci: float
    cr: float

    @property
    def consistent(self) -> bool:
        return self.cr < 0.10


@dataclass
class WeightResult:
    method: str
    weights: dict[str, float]
    details: dict = field(default_factory=dict)


def ahp_weights(matrix) -> AhpResult:
    """Principal-eigenvector weights of a reciprocal pairwise comparison matrix."""
    m = np.asarray(matrix, dtype=float)
    n = m.shape[0]
    if m.shape != (n, n):
        raise ValueError("AHP matrix must be square")
    eigvals, eigvecs = np.linalg.eig(m)
    idx = int(np.argmax(eigvals.real))
    lambda_max = float(eigvals[idx].real)
    w = np.abs(eigvecs[:, idx].real)
    w = w / w.sum()
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = RANDOM_INDEX.get(n, 1.49)
    cr = ci / ri if ri else 0.0
    return AhpResult(weights=w, lambda_max=lambda_max, ci=ci, cr=cr)


def entropy_weights(scores) -> np.ndarray:
    """Entropy Weight Method.

    `scores`: rows = observations (services or time windows), columns = criteria,
    already normalised so that higher is better. Criteria whose values vary more
    across observations carry more information and receive higher weight.
    """
    x = np.asarray(scores, dtype=float)
    n, m = x.shape
    if n < 2:
        return np.full(m, 1.0 / m)
    x = x + 1e-9
    p = x / x.sum(axis=0)
    e = -(p * np.log(p)).sum(axis=0) / np.log(n)
    d = 1.0 - e
    if d.sum() <= 1e-12:  # all criteria identical across observations
        return np.full(m, 1.0 / m)
    return d / d.sum()


def score_matrix(rows: list[dict[str, float | None]], dimensions: list[str]) -> np.ndarray:
    """Builds a dense matrix from dimension-score dicts, filling gaps with the column mean."""
    x = np.array([[np.nan if r.get(d) is None else r[d] for d in dimensions] for r in rows], dtype=float)
    for j in range(x.shape[1]):
        col = x[:, j]
        missing = np.isnan(col)
        col[missing] = col[~missing].mean() if (~missing).any() else 0.0
    return x


def resolve_weights(cfg: dict, observations: list[dict[str, float | None]] | None = None) -> WeightResult:
    """Returns dimension weights according to cfg['weighting']['method']."""
    dims = list(cfg["dimensions"])
    wcfg = cfg.get("weighting", {})
    method = wcfg.get("method", "fixed")

    def as_dict(arr) -> dict[str, float]:
        return {d: float(w) for d, w in zip(dims, arr)}

    if method == "fixed":
        fixed = wcfg["fixed"]
        total = sum(fixed[d] for d in dims)
        return WeightResult("fixed", {d: fixed[d] / total for d in dims})

    ahp = ahp_weights(wcfg["ahp_matrix"]) if method in ("ahp", "hybrid") else None
    ahp_info = {"lambda_max": ahp.lambda_max, "ci": ahp.ci, "cr": ahp.cr, "consistent": ahp.consistent} if ahp else {}

    if method == "ahp":
        return WeightResult("ahp", as_dict(ahp.weights), ahp_info)

    if not observations or len(observations) < 2:
        # Entropy needs at least two observations; fall back to AHP / fixed.
        fallback = ahp.weights if ahp is not None else ahp_weights(wcfg["ahp_matrix"]).weights
        return WeightResult(method, as_dict(fallback), {"note": "entropy fallback: fewer than 2 observations"})

    ent = entropy_weights(score_matrix(observations, dims))
    if method == "entropy":
        return WeightResult("entropy", as_dict(ent), {"entropy": as_dict(ent)})

    if method == "hybrid":
        alpha = float(wcfg.get("hybrid_alpha", 0.5))
        combined = alpha * ahp.weights + (1 - alpha) * ent
        combined = combined / combined.sum()
        return WeightResult("hybrid", as_dict(combined), {**ahp_info, "ahp": as_dict(ahp.weights), "entropy": as_dict(ent), "alpha": alpha})

    raise ValueError(f"Unknown weighting method: {method}")
