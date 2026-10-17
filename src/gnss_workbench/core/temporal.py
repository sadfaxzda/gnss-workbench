"""Bounded parity-space evidence; each epoch has four independent nuisances.

Only a candidate's range bias is locally linear in time. Receiver coordinates,
clock states, truth and future observations never enter this monitor. Consistency
and one-step predictive checks stop a long window spanning a detectable switch.
"""

from collections import deque
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.optimize import brentq
from scipy.stats import chi2, ncx2


@lru_cache(maxsize=512)
def threshold(dof: int, probability: float) -> float:
    return float(chi2.isf(probability, dof))


@lru_cache(maxsize=64)
def detection_noncentrality(dof: int, probability: float) -> float:
    """Noncentrality for 90% detection at the configured snapshot false alarm."""
    limit = threshold(dof, probability)
    root, _ = brentq(lambda value: ncx2.sf(limit, dof, value) - 0.9, 0, 1e4, full_output=True)
    return float(root)


def observability(h: np.ndarray, sigma: float, probability: float, keys: tuple[str, ...]) -> dict:
    dof = len(keys) - 4
    if dof <= 0:
        return dict(
            stage="fault_observability",
            redundancy=0,
            can_validate_exclusion=False,
            reason="四未知数恰定：无法用零残差证明无故障",
            satellites=[],
        )
    s = np.eye(len(keys)) - h @ np.linalg.pinv(h)
    power = detection_noncentrality(dof, probability)
    return dict(
        stage="fault_observability",
        redundancy=dof,
        can_validate_exclusion=len(keys) >= 6,
        detection_probability=0.9,
        false_alarm_probability=probability,
        satellites=[
            dict(
                sat_id=key,
                parity_redundancy=max(0.0, float(s[j, j])),
                detectable_bias_m=sigma * np.sqrt(power / s[j, j]) if s[j, j] > 1e-10 else None,
            )
            for j, key in enumerate(keys)
        ],
    )


@dataclass
class TemporalEvidence:
    keys: tuple[str, ...]
    epochs: int
    start_time: float
    statistics: np.ndarray
    passing: np.ndarray
    bias: np.ndarray
    drift: np.ndarray
    prediction_statistics: np.ndarray
    null_statistic: float
    detection_threshold: float
    residual_threshold: float
    current_support_threshold: float
    detected: bool

    def to_dict(self) -> dict:
        return dict(
            stage="temporal_parity",
            epochs=self.epochs,
            start_gpst_s=self.start_time,
            null_statistic=self.null_statistic,
            detection_threshold=self.detection_threshold,
            residual_threshold=self.residual_threshold,
            current_support_threshold=self.current_support_threshold,
            detected=self.detected,
        )


class TemporalParityMonitor:
    def __init__(self, window: int, max_gap_s: float, probability: float):
        self.window, self.max_gap_s, self.probability = window, max_gap_s, probability
        self.samples: deque[tuple[float, np.ndarray, np.ndarray, float]] = deque(maxlen=window)
        self.keys: tuple[str, ...] = ()

    def reset(self) -> None:
        self.samples.clear()
        self.keys = ()

    @staticmethod
    def _regress(t: np.ndarray, w: np.ndarray, r: np.ndarray, diagonal: np.ndarray):
        a = np.sum(w[:, None] * diagonal, axis=0)
        b = np.sum((w * t)[:, None] * diagonal, axis=0)
        c = np.sum((w * t**2)[:, None] * diagonal, axis=0)
        z = np.sum(w[:, None] * r, axis=0)
        v = np.sum((w * t)[:, None] * r, axis=0)
        det = np.maximum(a * c - b**2, 1e-20)
        intercept, drift = (c * z - b * v) / det, (a * v - b * z) / det
        return intercept, drift, c / det, z * intercept + v * drift

    def observe(
        self,
        time_s: float,
        keys: tuple[str, ...],
        h: np.ndarray,
        residual: np.ndarray,
        sigma: float,
    ) -> TemporalEvidence | None:
        order = np.argsort(keys)
        keys = tuple(keys[i] for i in order)
        if keys != self.keys or (
            self.samples and not 0 < time_s - self.samples[-1][0] <= self.max_gap_s
        ):
            self.reset()
        if len(keys) <= 4:
            self.reset()
            return None
        self.keys = keys
        h, residual = h[order], residual[order]
        projection = np.eye(len(keys)) - h @ np.linalg.pinv(h)
        residual = projection @ residual
        self.samples.append((time_s, residual, np.diag(projection), sigma))
        dof = len(keys) - 4
        current = float(residual @ residual / sigma**2)
        support = threshold(dof, self.probability**0.5)
        # Family-wise budget across all satellites and tested suffix lengths.
        family_probability = self.probability / (len(keys) * max(1, self.window - 2))
        detection_limit = threshold(2, family_probability)
        predictive_limit = threshold(dof, self.probability)
        # Longest consistent suffix; no use of future samples or state smoothing.
        samples = list(self.samples)
        for count in range(len(samples), 2, -1):
            records = samples[-count:]
            t = np.array([s[0] - time_s for s in records])
            r = np.array([s[1] for s in records])
            diagonal = np.maximum(np.array([s[2] for s in records]), 0)
            # A newly discovered larger scale also downweights earlier evidence.
            w = np.array([1 / max(sigma, s[3]) ** 2 for s in records])
            bias, drift, _, improvement = self._regress(t, w, r, diagonal)
            null = float(np.sum(w * np.sum(r**2, axis=1)))
            statistics = np.maximum(0, null - improvement)
            predicted, _, variance, _ = self._regress(t[:-1], w[:-1], r[:-1], diagonal[:-1])
            s = diagonal[-1]
            innovation = current - 2 * predicted * residual / sigma**2 + predicted**2 * s / sigma**2
            innovation -= (
                variance * (residual - predicted * s) ** 2 / (sigma**2 * (sigma**2 + variance * s))
            )
            innovation = np.maximum(0, innovation)
            limit = threshold(count * dof - 2, self.probability)
            passing = (statistics <= limit) & (innovation <= predictive_limit)
            winner = int(np.argmin(statistics))
            if passing[winner]:
                return TemporalEvidence(
                    keys,
                    count,
                    records[0][0],
                    statistics,
                    passing,
                    bias,
                    drift,
                    innovation,
                    null,
                    detection_limit,
                    limit,
                    support,
                    bool(null - statistics[winner] > detection_limit and current > support),
                )
        return None
