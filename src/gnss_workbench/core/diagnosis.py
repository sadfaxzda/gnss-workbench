"""Causal comparison of equal-dimensional single-fault hypotheses.

Only residual evidence is retained. Receiver coordinates, clock estimates, labels
and future observations are never stored here. Relative profile likelihood is an
engineering selection score, not a calibrated probability of correct exclusion.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp


@dataclass(frozen=True)
class LikelihoodDecision:
    selected: str | None
    method: str
    epochs: int
    start_time: float
    current_shares: dict[str, float]
    window_shares: dict[str, float]
    log_ratio: float
    reset_reason: str | None = None
    innovation_statistic: float | None = None
    innovation_satellite: str | None = None
    tentative: str | None = None
    tentative_source: str = "current"
    change_log_ratio: float | None = None
    change_start_time: float | None = None
    history_sigma_m: float | None = None


@dataclass
class EvidenceSample:
    time_s: float
    statistics: np.ndarray
    sigma_m: float
    biases: dict[str, tuple[float, float]]


class AmbiguityResolver:
    def __init__(self, window: int, max_gap_s: float, likelihood_ratio: float):
        self.window = window
        self.max_gap_s = max_gap_s
        self.log_threshold = math.log(likelihood_ratio)
        self.samples: deque[EvidenceSample] = deque(maxlen=window)
        self.satellites: tuple[str, ...] = ()
        self.keys: tuple[str, ...] = ()
        self.last_bias: dict[str, tuple[float, float]] = {}

    def reset(self) -> None:
        self.samples.clear()
        self.satellites = ()
        self.keys = ()
        self.last_bias.clear()

    @staticmethod
    def _compare(statistics: np.ndarray) -> tuple[int, np.ndarray, float]:
        log_likelihood = -0.5 * (statistics - statistics.min())
        winner = int(np.argmax(log_likelihood))
        shares = np.exp(log_likelihood - logsumexp(log_likelihood))
        others = np.delete(log_likelihood, winner)
        log_ratio = float(log_likelihood[winner] - logsumexp(others))
        return winner, shares, log_ratio

    def _rescale_history(self, sigma_m: float) -> None:
        # A scale estimate is causal, but may reveal that earlier evidence was
        # accumulated in overly optimistic units. Never amplify it on a decrease.
        for sample in self.samples:
            if sigma_m > sample.sigma_m:
                factor = (sample.sigma_m / sigma_m) ** 2
                sample.statistics = sample.statistics * factor
                sample.biases = {k: (b, v / factor) for k, (b, v) in sample.biases.items()}
                sample.sigma_m = sigma_m

    def observe(
        self,
        time_s: float,
        satellites: tuple[str, ...],
        statistics: dict[str, float],
        passing: set[str] | None = None,
        bias_estimates: dict[str, tuple[float, float]] | None = None,
        innovation_threshold: float | None = None,
        require_current_agreement: bool = False,
        use_unconfirmed_history: bool = False,
        detect_identity_change: bool = False,
        noise_sigma_m: float | None = None,
    ) -> LikelihoodDecision:
        """Compare all single-fault fits, including those failing the current gate.

        Each epoch profiles its own four receiver unknowns and fault amplitude.
        A short window assumes only that the fault identity persists. A decisive
        new current winner or rejection of the historical winner resets evidence.
        History cannot select a candidate
        contradicted by current evidence at the same likelihood-ratio threshold.
        A weak change of the minimum alone is not a demonstrated fault switch.
        When available, signed fault-amplitude innovations provide a separate
        change-point test without constraining receiver position or clock.
        The caller still checks current
        residuals, retained geometry and measurement redundancy before exclusion.
        """
        keys = tuple(sorted(statistics))
        satellites = tuple(sorted(satellites))
        values = np.array([statistics[key] for key in keys], dtype=float)
        reset_reason = None
        innovation = None
        innovation_satellite = None
        change_log_ratio = None
        change_start_time = None
        sigma_m = 1.0 if noise_sigma_m is None else noise_sigma_m
        if not math.isfinite(sigma_m) or sigma_m <= 0:
            raise ValueError("Noise scale must be finite and positive")
        if len(keys) < 2 or not np.all(np.isfinite(values)):
            self.reset()
            raise ValueError("Likelihood comparison needs all finite candidate statistics")
        if (
            keys != self.keys
            or satellites != self.satellites
            or (self.samples and not 0 < time_s - self.samples[-1].time_s <= self.max_gap_s)
        ):
            self.reset()
            reset_reason = "discontinuous_observations_or_time"
        if noise_sigma_m is not None:
            self._rescale_history(sigma_m)
            if self.samples:
                self.last_bias = dict(self.samples[-1].biases)
        current, current_shares, current_ratio = self._compare(values)
        # Instantaneous evidence can establish a new fault identity independently.
        if self.samples:
            previous, _, _ = self._compare(np.sum([s.statistics for s in self.samples], axis=0))
            previous_key = keys[previous]
            if (
                bias_estimates
                and previous_key in self.last_bias
                and innovation_threshold is not None
            ):
                old_bias, old_variance = self.last_bias[previous_key]
                new_bias, new_variance = bias_estimates[previous_key]
                # The current leave-one-out residual has n-5 degrees of freedom;
                # its independent signed amplitude innovation adds one. Under a
                # persistent constant bias and independent Gaussian noise this
                # sum is chi-square(n-4). Ramps can restart evidence, not freeze it.
                innovation = statistics[previous_key] + (new_bias - old_bias) ** 2 / (
                    old_variance + new_variance
                )
                innovation_satellite = previous_key
            if passing is not None and previous_key not in passing:
                reset_reason = "historical_identity_rejected"
            elif (
                innovation is not None
                and innovation_threshold is not None
                and innovation > innovation_threshold
            ):
                reset_reason = "fault_amplitude_change"
            elif current_ratio >= self.log_threshold and previous != current:
                reset_reason = "decisive_new_identity"
            if reset_reason:
                self.reset()
            elif detect_identity_change and previous != current and len(self.samples) >= 2:
                # Compare all possible suffix starts and alternative identities.
                # Mixture normalisation avoids treating each extra tested split
                # as an independent use of the full 20:1 decision budget.
                recent = [
                    *self.samples,
                    EvidenceSample(
                        time_s, values - values.min(), sigma_m, dict(bias_estimates or {})
                    ),
                ][-self.window :]
                matrix = np.array([s.statistics for s in recent])
                suffix = np.cumsum(matrix[::-1], axis=0)[:-1]
                alternatives = [j for j in range(len(keys)) if j != previous]
                gains = 0.5 * (suffix[:, previous, None] - suffix[:, alternatives])
                change_log_ratio = float(
                    np.logaddexp.reduce(gains.ravel())
                    - math.log((self.window - 1) * (len(keys) - 1))
                )
                length_index, identity_index = np.unravel_index(np.argmax(gains), gains.shape)
                new_identity = alternatives[identity_index]
                if (
                    change_log_ratio >= self.log_threshold
                    and new_identity == current
                    and (passing is None or keys[current] in passing)
                ):
                    retained = recent[-int(length_index + 1) :]
                    change_start_time = retained[0].time_s
                    # The current observation is appended below exactly once.
                    self.samples.clear()
                    self.samples.extend(retained[:-1])
                    reset_reason = "cumulative_identity_change"
        self.keys, self.satellites = keys, satellites
        self.last_bias = dict(bias_estimates or {})
        self.samples.append(
            EvidenceSample(time_s, values - values.min(), sigma_m, dict(bias_estimates or {}))
        )
        cumulative = np.sum([s.statistics for s in self.samples], axis=0)
        winner, window_shares, window_ratio = self._compare(cumulative)
        selected = None
        tentative, tentative_source = keys[current], "current"
        method = "unresolved"
        log_ratio = window_ratio
        if (
            use_unconfirmed_history
            and len(self.samples) > 1
            and (passing is None or keys[winner] in passing)
            and 0.5 * (values[winner] - values[current]) < self.log_threshold
        ):
            # Choosing a conditional estimate and certifying an identity are
            # separate decisions. Weak but consistent past evidence can reduce
            # snapshot toggling without meeting the confirmation threshold.
            tentative, tentative_source = keys[winner], "unconfirmed_history"
        if current_ratio >= self.log_threshold:
            selected, method, log_ratio = keys[current], "current_likelihood", current_ratio
        elif (
            window_ratio >= self.log_threshold
            and 0.5 * (values[winner] - values[current]) < self.log_threshold
        ):
            tentative, tentative_source = keys[winner], "history"
            if not require_current_agreement or winner == current:
                selected, method = keys[winner], "causal_likelihood"
        return LikelihoodDecision(
            selected,
            method,
            len(self.samples),
            self.samples[0].time_s,
            dict(zip(keys, map(float, current_shares), strict=True)),
            dict(zip(keys, map(float, window_shares), strict=True)),
            log_ratio,
            reset_reason,
            innovation,
            innovation_satellite,
            tentative,
            tentative_source,
            change_log_ratio,
            change_start_time,
            max(s.sigma_m for s in self.samples) if noise_sigma_m is not None else None,
        )
