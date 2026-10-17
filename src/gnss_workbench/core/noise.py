"""Causal scale estimation from disjoint, geometry-whitened parity differences.

No receiver state or selected FDE residual is used. A persistent satellite bias
cancels to first order across nearby epochs; isolated changes contaminate only
one pair and cannot dominate the median. This does not model rapidly varying,
correlated multipath as independent measurement noise.
"""

from collections import deque
from dataclasses import dataclass
from math import sqrt

import numpy as np
from scipy.stats import binom, chi2


@dataclass(frozen=True)
class NoiseEvidence:
    sigma_m: float
    pairs: int
    estimate_m: float | None
    nominal_tail_probability: float | None

    def to_dict(self) -> dict:
        return dict(
            stage="causal_noise_scale",
            sigma_m=self.sigma_m,
            independent_pairs=self.pairs,
            median_estimate_m=self.estimate_m,
            nominal_tail_probability=self.nominal_tail_probability,
        )


class ParityNoiseEstimator:
    """32 disjoint pairs, nominal scale floor, 5% median order-statistic test.

    The estimate used at epoch t contains only completed pairs before t. The
    lower median is an actual order statistic, with an exact iid Gaussian null
    tail (binomial CDF), rather than an interpolated quantile. Scale is enlarged
    only after >=3 pairs and evidence against the configured nominal floor.
    The resulting adaptive test is an engineering diagnostic, not certified RAIM.
    """

    def __init__(self, floor_m: float, max_gap_s: float, window: int = 32):
        self.floor_m, self.max_gap_s = floor_m, max_gap_s
        self.values: deque[float] = deque(maxlen=window)
        self.pending: tuple[np.ndarray, np.ndarray] | None = None
        self.keys: tuple[str, ...] = ()
        self.last_time: float | None = None
        self.dof = 0

    def reset(self) -> None:
        self.values.clear()
        self.pending = None
        self.keys = ()
        self.last_time = None
        self.dof = 0

    def estimate(self) -> NoiseEvidence:
        count = len(self.values)
        if count < 3:
            return NoiseEvidence(self.floor_m, count, None, None)
        rank = (count + 1) // 2
        median = sorted(self.values)[rank - 1]
        scale = sqrt(max(0, median) / float(chi2.ppf(0.5, self.dof)))
        # P(X_(rank) >= observed median | sigma=floor).
        cdf = float(chi2.cdf(median / self.floor_m**2, self.dof))
        probability = float(binom.cdf(rank - 1, count, cdf))
        sigma = max(self.floor_m, scale) if probability < 0.05 else self.floor_m
        return NoiseEvidence(sigma, count, scale, probability)

    def observe(
        self, time_s: float, satellites: tuple[str, ...], h: np.ndarray, residual: np.ndarray
    ) -> NoiseEvidence:
        order = np.argsort(satellites)
        keys = tuple(satellites[i] for i in order)
        if (
            keys != self.keys
            or self.last_time is None
            or not 0 < time_s - self.last_time <= self.max_gap_s
            or len(keys) <= 4
        ):
            self.reset()
        if len(keys) <= 4:
            return NoiseEvidence(self.floor_m, 0, None, None)
        self.keys, self.last_time, self.dof = keys, time_s, len(keys) - 4
        evidence = self.estimate()  # Never estimate sigma from the epoch being tested.
        h, residual = h[order], residual[order]
        basis = np.linalg.svd(h, full_matrices=True)[0][:, 4:]
        projection = basis @ basis.T
        if self.pending is None:
            self.pending = (projection @ residual, projection)
        else:
            old_residual, old_projection = self.pending
            delta = basis.T @ (residual - old_residual)
            covariance = np.eye(self.dof) + basis.T @ old_projection @ basis
            statistic = float(delta @ np.linalg.solve(covariance, delta))
            self.values.append(max(0.0, statistic))
            self.pending = None
        return evidence
