"""Algebraic current-epoch seeds, used only to retry a failed improved fit.

Squared range equations give A u = d + lambda/2, lambda = u.T M u,
M = diag(1,1,1,-1). This is Bancroft's two-root construction, not the
final corrected solution. No previous position or prescribed height is used.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class AlgebraicCandidate:
    state: np.ndarray
    real_root: bool

    @property
    def in_model_domain(self) -> bool:
        return bool(6e6 < np.linalg.norm(self.state[:3]) < 7e6)


def algebraic_candidates(satellites: np.ndarray, ranges: np.ndarray) -> list[AlgebraicCandidate]:
    # Scale to dimensionless units before the quadratic, avoiding 1e28 terms.
    if len(ranges) < 4:
        return []
    scale = float(np.median(np.linalg.norm(satellites, axis=1)))
    if not np.isfinite(scale) or scale <= 0 or len(ranges) < 4:
        return []
    xyz, p = satellites / scale, ranges / scale
    if not np.all(np.isfinite(p)) or np.max(np.abs(p)) > np.sqrt(np.finfo(float).max) / 4:
        return []
    design = np.column_stack((xyz, -p))
    d = 0.5 * (np.sum(xyz**2, axis=1) - p**2)
    values, _, rank, _ = np.linalg.lstsq(design, np.column_stack((np.ones(len(p)), d)), rcond=None)
    if rank < 4:
        return []
    a, b = values.T
    metric = np.array([1, 1, 1, -1])
    coefficients = [0.25 * (a * metric) @ a, (a * metric) @ b - 1, (b * metric) @ b]
    if not np.all(np.isfinite(coefficients)):
        return []
    candidates = []
    for root in np.roots(coefficients):
        # Complex conjugates have the same real centre. It is an approximation
        # for diagnosis/initialisation, never a valid algebraic position fix.
        state = (b + 0.5 * float(np.real(root)) * a) * scale
        if np.all(np.isfinite(state)) and not any(
            np.linalg.norm(state - c.state) < 1e-6 for c in candidates
        ):
            candidates.append(AlgebraicCandidate(state, bool(np.isreal(root))))
    return candidates


def algebraic_seeds(satellites: np.ndarray, ranges: np.ndarray) -> list[np.ndarray]:
    """Original real seeds in the same broad model domain as the ordinary solver."""
    return [
        c.state
        for c in algebraic_candidates(satellites, ranges)
        if c.real_root and c.in_model_domain
    ]
