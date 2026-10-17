"""Equal-weight SPP and bounded, explainable single/multiple-fault diagnosis.

No dataset names, fault schedules or reference receiver positions enter this module.
The previous fix is only an iteration initial value, never a measurement constraint.
"""

from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass, replace
from itertools import combinations
from typing import Any

import numpy as np
from scipy.stats import chi2

from .atmosphere import ionosphere, troposphere
from .coordinates import azimuth_elevation, geodetic, local_enu
from .diagnosis import AmbiguityResolver
from .ephemeris import C, rotate_to_receive, transmit_state
from .initialization import algebraic_candidates
from .models import Epoch, SatelliteDiagnostic, Solution, SolverConfig
from .noise import ParityNoiseEstimator
from .temporal import TemporalEvidence, TemporalParityMonitor, observability


class SolveError(Exception):
    def __init__(self, status: str, reason: str):
        super().__init__(reason)
        self.status = status


@dataclass
class PreparedObservation:
    sat_id: str
    pseudorange: float
    satellite: np.ndarray
    code_clock: float


@dataclass
class Fit:
    state: np.ndarray
    h: np.ndarray
    residual: np.ndarray
    azimuth: np.ndarray
    elevation: np.ndarray
    observations: list[PreparedObservation]
    pdop: float


class PositioningEngine:
    def __init__(self, navigation: dict[str, Any], config: SolverConfig | None = None):
        self.navigation = navigation
        self.config = config or SolverConfig()
        self._initial = np.zeros(4)
        self._ambiguity = AmbiguityResolver(
            self.config.fde_history_epochs,
            self.config.fde_history_max_gap_s,
            self.config.fde_likelihood_ratio,
        )
        self._noise = ParityNoiseEstimator(
            self.config.noise_sigma_m, self.config.fde_history_max_gap_s
        )
        self._sigma = self.config.noise_sigma_m
        self._temporal = TemporalParityMonitor(
            self.config.fde_history_epochs,
            self.config.fde_history_max_gap_s,
            self.config.false_alarm_probability,
        )
        self._temporal_evidence: TemporalEvidence | None = None

    def _prepare(self, epoch: Epoch) -> list[PreparedObservation]:
        result = []
        for obs in epoch.observations:
            eph = self.navigation["ephemerides"].get(obs.sat_id)
            if eph is None or eph.get("sv_health", 0) != 0:
                raise SolveError("INVALID_EPHEMERIS", f"{obs.sat_id} 无可用健康星历")
            dt = (epoch.gps_week - eph["gps_week"]) * 604800 + epoch.gps_sow - eph["toe"]
            if abs(dt) > 7200:
                raise SolveError("INVALID_EPHEMERIS", f"{obs.sat_id} 超出配套星历两小时使用范围")
            xyz, clock = transmit_state(eph, epoch.gps_sow, obs.pseudorange_m)
            result.append(PreparedObservation(obs.sat_id, obs.pseudorange_m, xyz, clock))
        return result

    def _linearize(
        self, observations: list[PreparedObservation], state: np.ndarray, sow: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        receiver, clock_bias = state[:3], state[3]
        near_surface = 6e6 < np.linalg.norm(receiver) < 7e6
        lat, lon, height = geodetic(receiver) if near_surface else (0.0, 0.0, 0.0)
        h, residual, azimuths, elevations = [], [], [], []
        for obs in observations:
            tau = (obs.pseudorange + C * obs.code_clock - clock_bias) / C
            satellite = rotate_to_receive(obs.satellite, tau)
            delta = receiver - satellite
            rho = float(np.linalg.norm(delta))
            if rho < 1 or not math.isfinite(rho):
                raise SolveError("INVALID_GEOMETRY", "几何距离无法计算")
            az, el = azimuth_elevation(receiver, satellite) if near_surface else (0.0, math.pi / 2)
            atmosphere = 0.0
            if near_surface and el > 0:
                atmosphere = ionosphere(
                    lat,
                    lon,
                    az,
                    el,
                    sow - clock_bias / C,
                    self.navigation["alpha"],
                    self.navigation["beta"],
                )
                atmosphere += troposphere(lat, height, el)
            predicted = rho + clock_bias - C * obs.code_clock + atmosphere
            h.append([*(delta / rho), 1.0])
            residual.append(obs.pseudorange - predicted)
            azimuths.append(az)
            elevations.append(el)
        return np.array(h), np.array(residual), np.array(azimuths), np.array(elevations)

    def _fit(
        self,
        observations: list[PreparedObservation],
        sow: float,
        initial: np.ndarray,
        weights: np.ndarray | None = None,
    ) -> Fit:
        if len(observations) < 4:
            raise SolveError("INVALID_INSUFFICIENT", "参与解算的卫星不足四颗")
        state = initial.copy()
        root_weights = np.ones(len(observations)) if weights is None else np.sqrt(weights)
        if root_weights.shape != (len(observations),) or not np.all(np.isfinite(root_weights)):
            raise SolveError("INVALID_DATA", "Invalid robust weights")
        for _ in range(self.config.max_iterations):
            h, residual, _, _ = self._linearize(observations, state, sow)
            step, _, rank, singular = np.linalg.lstsq(
                h * root_weights[:, None], residual * root_weights, rcond=None
            )
            if rank < 4 or singular[-1] < 1e-8:
                raise SolveError("INVALID_GEOMETRY", "几何矩阵秩不足或严重病态")
            state += step
            if not np.all(np.isfinite(state)) or np.linalg.norm(state[:3]) > 1e9:
                raise SolveError("INVALID_CONVERGENCE", "迭代状态发散")
            if np.linalg.norm(step) < self.config.convergence_m:
                break
        else:
            raise SolveError("INVALID_CONVERGENCE", "达到迭代上限，未满足收敛条件")
        h, residual, az, el = self._linearize(observations, state, sow)
        if not 6e6 < np.linalg.norm(state[:3]) < 7e6:
            raise SolveError("INVALID_CONVERGENCE", "收敛位置超出地表教学模型适用范围")
        _, singular, vt = np.linalg.svd(h, full_matrices=False)
        q = (vt.T / singular**2) @ vt
        pdop = float(np.sqrt(np.trace(q[:3, :3])))
        if not math.isfinite(pdop) or pdop > 1e4:
            raise SolveError("INVALID_GEOMETRY", "几何条件无法支持可靠定位")
        return Fit(state, h, residual, az, el, observations, pdop)

    def _solution(self, epoch: Epoch, fit: Fit) -> Solution:
        n = len(fit.observations)
        status = "NO_REDUNDANCY" if n == 4 else "VALID"
        reason = "四颗卫星可解，但没有单历元观测冗余" if n == 4 else "残差与观测模型一致"
        if fit.pdop > self.config.pdop_warning:
            status, reason = "GEOMETRY_WARNING", "卫星几何分布较差，位置误差可能被放大"
        dof = n - 4
        statistic = float(fit.residual @ fit.residual / self.config.noise_sigma_m**2)
        threshold = float(chi2.ppf(1 - self.config.false_alarm_probability, dof)) if dof else None
        leverage = np.sum(fit.h * np.linalg.pinv(fit.h).T, axis=1)
        diagnostics = [
            SatelliteDiagnostic(
                obs.sat_id,
                float(fit.residual[i]),
                float(
                    fit.residual[i]
                    / (self.config.noise_sigma_m * math.sqrt(max(1e-10, 1 - leverage[i])))
                )
                if dof
                else 0.0,
                math.degrees(float(fit.elevation[i])),
                math.degrees(float(fit.azimuth[i])),
            )
            for i, obs in enumerate(fit.observations)
        ]
        return Solution(
            epoch.epoch_id,
            epoch.gps_week,
            epoch.gps_sow,
            status,
            *map(float, fit.state),
            n_used=n,
            pdop=fit.pdop,
            residual_rms_m=float(np.sqrt(np.mean(fit.residual**2))),
            diagnostics=diagnostics,
            reason=reason,
            test_statistic=statistic,
            test_threshold=threshold,
            dof=dof,
        )

    def solve(self, epoch: Epoch) -> tuple[Solution, Solution]:
        started = time.perf_counter()
        n = len(epoch.observations)
        if epoch.data_error:
            self._ambiguity.reset()
            self._noise.reset()
            self._temporal.reset()
            self._temporal_evidence = None
            invalid = Solution(
                epoch.epoch_id,
                epoch.gps_week,
                epoch.gps_sow,
                "INVALID_DATA",
                reason=epoch.data_error,
            )
            invalid.processing_ms = (time.perf_counter() - started) * 1000
            return invalid, copy.deepcopy(invalid)
        if n < 4:
            self._ambiguity.reset()
            self._noise.reset()
            self._temporal.reset()
            self._temporal_evidence = None
            status = "NO_OBSERVATIONS" if n == 0 else "INVALID_INSUFFICIENT"
            reason = (
                "当前历元没有卫星观测" if n == 0 else "不足四颗卫星，无法独立解算三维位置与钟差"
            )
            invalid = Solution(
                epoch.epoch_id, epoch.gps_week, epoch.gps_sow, status, n_used=n, reason=reason
            )
            invalid.processing_ms = (time.perf_counter() - started) * 1000
            return invalid, copy.deepcopy(invalid)
        try:
            observations = self._prepare(epoch)
            fit = self._fit(observations, epoch.gps_sow, self._initial)
            above_mask = [
                o
                for o, el in zip(fit.observations, fit.elevation, strict=True)
                if math.degrees(el) >= self.config.elevation_mask_deg
            ]
            if len(above_mask) != n:
                fit = self._fit(above_mask, epoch.gps_sow, fit.state)
            baseline = self._solution(epoch, fit)
            baseline.reason = (
                "普通等权最小二乘；未启用异常剔除"
                if baseline.status == "VALID"
                else baseline.reason
            )
            baseline.processing_ms = (time.perf_counter() - started) * 1000
            improved = copy.deepcopy(baseline)
            improved.reason = (
                "残差与观测模型一致" if baseline.status == "VALID" else baseline.reason
            )
            if self.config.enable_fde:
                if self.config.adaptive_noise and self.config.algorithm != "single_fde":
                    noise = self._noise.observe(
                        epoch.gps_week * 604800 + epoch.gps_sow,
                        tuple(o.sat_id for o in fit.observations),
                        fit.h,
                        fit.residual,
                    )
                    self._sigma = noise.sigma_m
                else:
                    self._noise.reset()
                    noise = None
                    self._sigma = self.config.noise_sigma_m
                if (
                    self.config.temporal_parity
                    and self.config.algorithm != "single_fde"
                    and baseline.status != "GEOMETRY_WARNING"
                ):
                    self._temporal_evidence = self._temporal.observe(
                        epoch.gps_week * 604800 + epoch.gps_sow,
                        tuple(o.sat_id for o in fit.observations),
                        fit.h,
                        fit.residual,
                        self._sigma,
                    )
                else:
                    self._temporal.reset()
                    self._temporal_evidence = None
                improved = self._diagnose(epoch, fit, improved)
                if self._temporal_evidence is not None:
                    improved.algorithm_trace.append(self._temporal_evidence.to_dict())
                if self.config.temporal_parity:
                    improved.algorithm_trace.append(
                        observability(
                            fit.h,
                            self._sigma,
                            self.config.false_alarm_probability,
                            tuple(o.sat_id for o in fit.observations),
                        )
                    )
                if noise is not None:
                    improved.algorithm_trace.append(noise.to_dict())
                    if noise.sigma_m > self.config.noise_sigma_m:
                        improved.reason += (
                            f"；诊断噪声尺度 {noise.sigma_m:.2f} m"
                            f"（过去 {noise.pairs} 个独立历元对估计，普通解不变）"
                        )
                improved.algorithm = self.config.algorithm
            else:
                self._ambiguity.reset()
                self._noise.reset()
                self._temporal.reset()
                self._temporal_evidence = None
                improved.reason = "消融模式：关闭异常检测与剔除，结果与基线一致"
            improved.processing_ms = (time.perf_counter() - started) * 1000
            candidate = improved if improved.has_position else baseline
            if candidate.status in {"VALID", "FAULT_EXCLUDED", "NO_REDUNDANCY"}:
                self._initial = np.array(
                    [candidate.x_m, candidate.y_m, candidate.z_m, candidate.clock_bias_m],
                    dtype=float,
                )
            return baseline, improved
        except (SolveError, np.linalg.LinAlgError) as error:
            self._ambiguity.reset()
            self._noise.reset()
            self._temporal.reset()
            self._temporal_evidence = None
            status = error.status if isinstance(error, SolveError) else "INVALID_GEOMETRY"
            invalid = Solution(
                epoch.epoch_id, epoch.gps_week, epoch.gps_sow, status, n_used=n, reason=str(error)
            )
            invalid.processing_ms = (time.perf_counter() - started) * 1000
            improved = copy.deepcopy(invalid)
            if (
                status in {"INVALID_CONVERGENCE", "INVALID_INSUFFICIENT"}
                and self.config.enable_fde
                and self.config.algebraic_recovery
                and self.config.algorithm != "single_fde"
            ):
                improved = self._recover_convergence(epoch, improved)
                improved.processing_ms = (time.perf_counter() - started) * 1000
            return invalid, improved

    def _recover_convergence(self, epoch: Epoch, invalid: Solution) -> Solution:
        """Retry current observations only; never alter the ordinary result/initial.

        The algebraic approximation omits atmosphere/rotation, so every seed must
        be refined using the unchanged full course model before outputting a fix.
        """
        observations = self._prepare(epoch)
        candidates = algebraic_candidates(
            np.array([o.satellite for o in observations]),
            np.array([o.pseudorange + C * o.code_clock for o in observations]),
        )
        if not self.config.complete_geometry_diagnosis:
            candidates = [c for c in candidates if c.real_root and c.in_model_domain]
        evidence: dict[str, Any] = dict(
            stage="algebraic_recovery", seeds=len(candidates), attempts=[], candidates=[]
        )
        seed_pdops = []
        for candidate in candidates:
            state = candidate.state
            try:
                h, _, _, _ = self._linearize(observations, state, epoch.gps_sow)
                singular = np.linalg.svd(h, compute_uv=False)
                seed_pdop = float(np.linalg.norm(np.linalg.pinv(h)[:3]))
                seed_pdops.append(seed_pdop if singular[-1] >= 1e-8 else float("inf"))
                evidence["candidates"].append(
                    dict(
                        real_root=candidate.real_root,
                        in_model_domain=candidate.in_model_domain,
                        radius_m=float(np.linalg.norm(state[:3])),
                        pdop=seed_pdop if singular[-1] >= 1e-8 else None,
                        rank_deficient=bool(singular[-1] < 1e-8),
                    )
                )
                if not candidate.in_model_domain:
                    continue
                fit = self._fit(observations, epoch.gps_sow, state)
                retained = [
                    o
                    for o, el in zip(fit.observations, fit.elevation, strict=True)
                    if math.degrees(el) >= self.config.elevation_mask_deg
                ]
                if len(retained) != len(observations):
                    fit = self._fit(retained, epoch.gps_sow, fit.state)
                self._sigma = self.config.noise_sigma_m
                solution = self._diagnose(epoch, fit, self._solution(epoch, fit))
                evidence["attempts"].append(dict(status=solution.status, pdop=fit.pdop))
                solution.algorithm_trace.append(evidence)
                if self.config.temporal_parity:
                    solution.algorithm_trace.append(
                        observability(
                            fit.h,
                            self._sigma,
                            self.config.false_alarm_probability,
                            tuple(o.sat_id for o in fit.observations),
                        )
                    )
                solution.algorithm = self.config.algorithm
                solution.reason += "；当前伪距代数初值经完整模型重新收敛，普通解保留原状态"
                return solution
            except (SolveError, np.linalg.LinAlgError) as error:
                evidence["attempts"].append(
                    dict(
                        status=error.status
                        if isinstance(error, SolveError)
                        else "INVALID_GEOMETRY",
                        reason=str(error),
                    )
                )
        evidence["seed_pdops"] = [p if math.isfinite(p) else None for p in seed_pdops]
        if seed_pdops and all(d > self.config.pdop_warning for d in seed_pdops):
            invalid.status = "INVALID_GEOMETRY"
            invalid.reason = (
                f"当前伪距代数候选的几何PDOP均>{self.config.pdop_warning:g}或秩不足"
                "，没有通过完整模型验证的地表解；候选及近似根仅作诊断，严重病态，拒绝输出位置"
            )
        invalid.algorithm_trace.append(evidence)
        return invalid

    def _diagnose(self, epoch: Epoch, fit: Fit, result: Solution) -> Solution:
        if self.config.algorithm == "single_fde":
            self._ambiguity.reset()
            return self._single_fde(epoch, fit, result)
        self._rescale_diagnostics(result)
        temporal_alarm = self._temporal_evidence is not None and self._temporal_evidence.detected
        if (
            result.test_threshold is None
            or result.test_statistic is None
            or (result.test_statistic <= result.test_threshold and not temporal_alarm)
        ):
            self._ambiguity.reset()
            if result.status == "NO_REDUNDANCY":
                result.reason += "；四未知数恰定，零残差不能证明无故障，不能安全剔星"
            return result
        if result.status == "GEOMETRY_WARNING":
            self._ambiguity.reset()
            result.reason += "；残差异常，几何不足以支持自动归因"
            return result
        result.status = "SUSPECT"
        if len(fit.observations) < 6:
            self._ambiguity.reset()
            result.reason = (
                "时序奇偶空间检验发现持续不一致" if temporal_alarm else "当前残差检验异常"
            ) + "；五星仅一个验证自由度，剔一星后没有验证冗余，故障身份未确认，不盲目剔星"
            return result
        proposal_weights = None
        if self.config.algorithm == "adaptive_gnc":
            proposal_weights, result.algorithm_trace = self._adaptive_gnc(epoch, fit)
        return self._consensus(epoch, fit, result, proposal_weights)

    def _rescale_diagnostics(self, result: Solution) -> None:
        """Change only improved diagnostic units; baseline OLS stays untouched."""
        ratio = self.config.noise_sigma_m / self._sigma
        if result.test_statistic is not None:
            result.test_statistic *= ratio**2
        for diagnostic in result.diagnostics:
            diagnostic.normalized_residual *= ratio

    def _single_fde(self, epoch: Epoch, fit: Fit, result: Solution) -> Solution:
        if (
            result.test_threshold is None
            or result.test_statistic is None
            or result.test_statistic <= result.test_threshold
        ):
            return result
        if result.status == "GEOMETRY_WARNING":
            result.reason += "；残差检验同时异常，暂不自动定位故障卫星"
            return result
        result.status = "SUSPECT"
        result.reason = "全局残差检验超限，证据不足以唯一定位故障"
        if len(fit.observations) < 6:
            result.reason = "残差检验超限，但剔除一星后缺少验证冗余"
            return result
        candidates: list[tuple[str, Fit, float]] = []
        scores: list[dict[str, Any]] = []
        for removed in fit.observations:
            retained = [o for o in fit.observations if o.sat_id != removed.sat_id]
            try:
                candidate = self._fit(retained, epoch.gps_sow, fit.state)
            except SolveError:
                continue
            dof = len(retained) - 4
            statistic = float(
                candidate.residual @ candidate.residual / self.config.noise_sigma_m**2
            )
            threshold = float(chi2.ppf(1 - self.config.false_alarm_probability, dof))
            passed = statistic <= threshold and candidate.pdop <= self.config.pdop_warning
            scores.append(
                {
                    "sat_id": removed.sat_id,
                    "statistic": statistic,
                    "threshold": threshold,
                    "passed": passed,
                    "pdop": candidate.pdop,
                }
            )
            if passed:
                candidates.append((removed.sat_id, candidate, statistic))
        result.candidate_scores = scores
        # A second passing candidate would leave attribution ambiguous. Do not hide it.
        if len(candidates) != 1:
            result.reason = f"残差检验超限；{len(candidates)} 个剔星假设通过验证，无法唯一归因"
            return result
        removed_id, best_fit, _ = candidates[0]
        diagnosed = self._solution(epoch, best_fit)
        diagnosed.status = "FAULT_EXCLUDED"
        diagnosed.flagged_sats = [removed_id]
        diagnosed.excluded_sats = [removed_id]
        diagnosed.candidate_scores = scores
        diagnosed.reason = f"仅剔除 {removed_id} 后残差一致性检验通过，且保留验证冗余"
        _, residual_all, az_all, el_all = self._linearize(
            fit.observations, best_fit.state, epoch.gps_sow
        )
        index = next(i for i, o in enumerate(fit.observations) if o.sat_id == removed_id)
        diagnosed.diagnostics.append(
            SatelliteDiagnostic(
                removed_id,
                float(residual_all[index]),
                float(residual_all[index] / self.config.noise_sigma_m),
                math.degrees(float(el_all[index])),
                math.degrees(float(az_all[index])),
                weight=0.0,
                excluded=True,
            )
        )
        diagnosed.diagnostics.sort(key=lambda d: d.sat_id)
        return diagnosed

    def _adaptive_gnc(self, epoch: Epoch, fit: Fit) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """Bounded GM continuation inspired by SAC-GNC (ICCV 2025).

        This is a deterministic GNSS adaptation, not a reproduction of SAC-GNC.
        Three annealing rates compete in a width-three beam. MSAC scores retain
        the best hypothesis across all depths. Final acceptance is independently
        checked by unweighted subset fits in _consensus; weights alone never
        certify a fault or an integrity guarantee.
        """
        cutoff2 = (3 * self._sigma) ** 2
        shape2 = max(cutoff2, float(np.max(fit.residual**2)))
        beam = [(fit, shape2)]
        best_score = float(np.minimum(fit.residual**2, cutoff2).sum())
        best_weights = np.ones(len(fit.observations))
        trace: list[dict[str, Any]] = []
        for depth in range(6):
            children: list[tuple[float, Fit, float]] = []
            for parent, parent_shape in beam:
                for rate in (1.4, 2.6, 4.9):
                    shape = max(cutoff2, parent_shape / rate**2)
                    candidate = parent
                    try:
                        for _ in range(5):
                            weights = (shape / (shape + candidate.residual**2)) ** 2
                            updated = self._fit(
                                fit.observations,
                                epoch.gps_sow,
                                candidate.state,
                                np.maximum(weights, 1e-6),
                            )
                            change = float(np.linalg.norm(updated.state - candidate.state))
                            candidate = updated
                            if change < 0.001:
                                break
                    except (SolveError, np.linalg.LinAlgError):
                        continue
                    weights = (shape / (shape + candidate.residual**2)) ** 2
                    score = float(np.minimum(candidate.residual**2, cutoff2).sum())
                    trace.append(
                        {
                            "depth": depth,
                            "annealing_rate": rate,
                            "shape_m": math.sqrt(shape),
                            "msac_score_m2": score,
                            "weights": {
                                o.sat_id: float(w)
                                for o, w in zip(fit.observations, weights, strict=True)
                            },
                        }
                    )
                    if score < best_score:
                        best_score, best_weights = score, weights.copy()
                    if shape > cutoff2:
                        children.append((score, candidate, shape))
            if not children:
                break
            children.sort(key=lambda item: item[0])
            beam = [(candidate, shape) for _, candidate, shape in children[:3]]
        return best_weights, trace

    def _consensus(
        self,
        epoch: Epoch,
        fit: Fit,
        result: Solution,
        proposal_weights: np.ndarray | None,
    ) -> Solution:
        """Minimal-cardinality FDE with complete, bounded hypothesis evidence.

        A candidate must retain >= 5 satellites, pass the unweighted residual
        test and have acceptable unweighted PDOP. Multiple passing single-fault
        candidates need explicit likelihood evidence; unresolved ambiguity and
        truncated searches stay SUSPECT. Multiple-fault attribution stays unique.
        No probabilistic integrity claim is made for multiple-hypothesis testing.
        """
        observations = fit.observations
        # Signed single-fault estimates in residual (parity) space. These retain
        # only fault-amplitude information; no receiver-state prior is introduced.
        projection = np.eye(len(observations)) - fit.h @ np.linalg.pinv(fit.h)
        parity_residual = projection @ fit.residual
        if proposal_weights is not None:
            for diagnostic, weight in zip(result.diagnostics, proposal_weights, strict=True):
                diagnostic.robust_weight = float(weight)
        scores: list[dict[str, Any]] = []
        for size in range(1, min(self.config.max_faults, len(observations) - 5) + 1):
            hypotheses = list(combinations(range(len(observations)), size))
            if proposal_weights is not None:
                hypotheses.sort(
                    key=lambda indices: sum(float(proposal_weights[i]) for i in indices)
                )
            passed: list[tuple[tuple[int, ...], Fit]] = []
            for indices in hypotheses:
                if len(scores) >= self.config.max_hypotheses:
                    self._ambiguity.reset()
                    result.search_complete = False
                    result.reason = "达到假设检验预算；搜索不完整，不能确认故障归因"
                    result.candidate_scores = scores
                    return result
                removed_ids = [observations[i].sat_id for i in indices]
                retained = [o for i, o in enumerate(observations) if i not in indices]
                evidence: dict[str, Any] = {
                    "sat_id": "+".join(removed_ids),
                    "excluded_sats": removed_ids,
                    "passed": False,
                    "statistic": None,
                    "threshold": None,
                    "pdop": None,
                }
                if size == 1:
                    j = indices[0]
                    redundancy = max(float(projection[j, j]), 1e-12)
                    correlations = np.abs(projection[j]) / np.sqrt(
                        redundancy * np.maximum(np.diag(projection), 1e-12)
                    )
                    correlations[j] = -1
                    neighbour = int(np.argmax(correlations))
                    correlation = float(np.clip(correlations[neighbour], 0, 1))
                    evidence.update(
                        fault_bias_m=float(parity_residual[j] / redundancy),
                        fault_variance_m2=self._sigma**2 / redundancy,
                        nearest_fault_alternative=observations[neighbour].sat_id,
                        fault_direction_correlation=correlation,
                        fault_direction_angle_deg=math.degrees(math.acos(correlation)),
                    )
                try:
                    candidate = self._fit(retained, epoch.gps_sow, fit.state)
                    statistic = float(candidate.residual @ candidate.residual / self._sigma**2)
                    threshold = float(
                        chi2.ppf(1 - self.config.false_alarm_probability, len(retained) - 4)
                    )
                    accepted = statistic <= threshold and candidate.pdop <= self.config.pdop_warning
                    evidence.update(
                        statistic=statistic,
                        threshold=threshold,
                        pdop=candidate.pdop,
                        passed=accepted,
                    )
                    if accepted:
                        passed.append((indices, candidate))
                except (SolveError, np.linalg.LinAlgError) as error:
                    evidence["failure"] = str(error)
                scores.append(evidence)
            result.candidate_scores = scores
            decision = None
            if size == 1:
                if (
                    self.config.resolve_ambiguity
                    and passed
                    and all(s["statistic"] is not None for s in scores)
                ):
                    decision = self._ambiguity.observe(
                        epoch.gps_week * 604800 + epoch.gps_sow,
                        tuple(o.sat_id for o in observations),
                        {s["sat_id"]: s["statistic"] for s in scores},
                        {s["sat_id"] for s in scores if s["passed"]},
                        {s["sat_id"]: (s["fault_bias_m"], s["fault_variance_m2"]) for s in scores}
                        if self.config.fde_change_detection
                        else None,
                        result.test_threshold if self.config.fde_change_detection else None,
                        require_current_agreement=self.config.fde_change_detection,
                        use_unconfirmed_history=self.config.use_unconfirmed_history,
                        detect_identity_change=self.config.sequential_change_detection
                        and self.config.fde_change_detection,
                        noise_sigma_m=self._sigma if self.config.rescale_history else None,
                    )
                    temporal = self._temporal_evidence
                    if (
                        temporal is not None
                        and temporal.detected
                        and result.test_statistic is not None
                        and result.test_threshold is not None
                        and (
                            result.test_statistic <= result.test_threshold
                            or (self.config.coherent_proposals and decision.selected is None)
                        )
                        and decision.method != "current_likelihood"
                    ):
                        winner, shares, log_ratio = AmbiguityResolver._compare(temporal.statistics)
                        key = temporal.keys[winner]
                        by_key = {s["sat_id"]: s for s in scores}
                        current_best = min(scores, key=lambda s: s["statistic"])
                        if (
                            temporal.passing[winner]
                            and by_key[key]["passed"]
                            and 0.5 * (by_key[key]["statistic"] - current_best["statistic"])
                            < math.log(self.config.fde_likelihood_ratio)
                        ):
                            weak_snapshot = result.test_statistic <= result.test_threshold
                            if weak_snapshot or log_ratio >= math.log(
                                self.config.fde_likelihood_ratio
                            ):
                                # Strong-fault profile evidence is a conditional
                                # position proposal only. It never upgrades an
                                # unresolved identity or replaces a confirmed one.
                                confirmed = (
                                    weak_snapshot
                                    and log_ratio >= math.log(self.config.fde_likelihood_ratio)
                                    and (
                                        not self.config.fde_change_detection
                                        or current_best["sat_id"] == key
                                    )
                                )
                                decision = replace(
                                    decision,
                                    selected=key if confirmed else None,
                                    method="coherent_likelihood" if confirmed else "unresolved",
                                    tentative=key,
                                    tentative_source="coherent_history"
                                    if weak_snapshot
                                    else "coherent_proposal",
                                    epochs=temporal.epochs,
                                    start_time=temporal.start_time,
                                    log_ratio=log_ratio,
                                    window_shares=dict(
                                        zip(temporal.keys, map(float, shares), strict=True)
                                    ),
                                )
                    for score in scores:
                        key = score["sat_id"]
                        score.update(
                            current_likelihood_share=decision.current_shares[key],
                            window_likelihood_share=decision.window_shares[key],
                            evidence_epochs=decision.epochs,
                            evidence_start_gpst_s=decision.start_time,
                            selection_log_ratio=decision.log_ratio,
                            required_log_ratio=math.log(self.config.fde_likelihood_ratio),
                            history_reset_reason=decision.reset_reason,
                            change_log_ratio=decision.change_log_ratio,
                            change_start_gpst_s=decision.change_start_time,
                            innovation_statistic=decision.innovation_statistic,
                            innovation_satellite=decision.innovation_satellite,
                            innovation_threshold=result.test_threshold,
                            history_sigma_m=decision.history_sigma_m,
                        )
                        if temporal is not None:
                            j = temporal.keys.index(key)
                            score.update(
                                temporal_statistic=float(temporal.statistics[j]),
                                temporal_passed=bool(temporal.passing[j]),
                                temporal_bias_m=float(temporal.bias[j]),
                                temporal_drift_mps=float(temporal.drift[j]),
                                temporal_prediction_statistic=float(
                                    temporal.prediction_statistics[j]
                                ),
                            )
                else:
                    self._ambiguity.reset()
            if not passed:
                continue
            chosen = passed[0] if len(passed) == 1 else None
            selection_method = "unique_subset"
            # A candidate just outside the absolute gate remains an alternative.
            # Uniqueness of passing subsets alone is not strong identity evidence.
            if (
                size == 1
                and len(passed) == 1
                and decision is not None
                and self.config.strict_fde_confirmation
                and decision.selected != observations[passed[0][0][0]].sat_id
            ):
                if not self.config.provisional_fde:
                    result.reason = "唯一通过子集与其他假设的相对证据不足，保留 SUSPECT"
                    return result
                selection_method = "provisional_likelihood"
            if len(passed) != 1:
                if decision and decision.selected:
                    chosen = next(
                        (p for p in passed if observations[p[0][0]].sat_id == decision.selected),
                        None,
                    )
                    selection_method = decision.method
                if chosen is None:
                    if size == 1 and decision and self.config.provisional_fde:
                        # Maximum-likelihood conditional estimate, explicitly not
                        # a confirmed fault identity. Never mark every candidate
                        # merely to make detection recall look better.
                        chosen = next(
                            (
                                p
                                for p in passed
                                if observations[p[0][0]].sat_id == decision.tentative
                            ),
                            None,
                        )
                        if chosen is None:
                            result.reason = "相对似然领先候选未通过当前验证，保留 SUSPECT"
                            return result
                        selection_method = "provisional_likelihood"
                    else:
                        result.reason = f"{size} 星故障模型有 {len(passed)} 个假设通过；似然证据不足或当前证据矛盾，保留 SUSPECT"
                        return result
            assert chosen is not None
            indices, best = chosen
            diagnosed = self._solution(epoch, best)
            self._rescale_diagnostics(diagnosed)
            diagnosed.status = (
                "SUSPECT" if selection_method == "provisional_likelihood" else "FAULT_EXCLUDED"
            )
            diagnosed.excluded_sats = [observations[i].sat_id for i in indices]
            diagnosed.flagged_sats = diagnosed.excluded_sats.copy()
            diagnosed.candidate_scores = scores
            diagnosed.algorithm_trace = result.algorithm_trace
            # Expose the consequence of an ambiguous identity in position space.
            # These are differences between current independent subset fits,
            # never truth errors, posterior probabilities or protection levels.
            separations = {
                tuple(observations[i].sat_id for i in candidate_indices): float(
                    np.linalg.norm(local_enu(candidate_fit.state[:3], best.state[:3])[:2])
                )
                for candidate_indices, candidate_fit in passed
            }
            for score in scores:
                score["selected"] = score["excluded_sats"] == diagnosed.excluded_sats
                score["candidate_horizontal_separation_m"] = separations.get(
                    tuple(score["excluded_sats"])
                )
                if score["selected"]:
                    score["selection_method"] = selection_method
                    if selection_method == "provisional_likelihood" and decision:
                        score["provisional_source"] = (
                            "unique_passing" if len(passed) == 1 else decision.tentative_source
                        )
            if selection_method == "unique_subset":
                diagnosed.reason = (
                    f"最小 {size} 星故障假设唯一通过；剔除后保留 {diagnosed.dof} 个验证自由度"
                )
            elif selection_method == "provisional_likelihood":
                diagnosed.reason = (
                    f"{len(passed)} 个单星候选通过；采用相对似然领先子集暂定剔除 "
                    f"{diagnosed.excluded_sats[0]}，身份尚未确认，保留 SUSPECT；"
                    "当前历元独立重算，可能误选，请同时查看候选证据"
                )
            else:
                assert decision is not None
                evidence_count = 1 if selection_method == "current_likelihood" else decision.epochs
                diagnosed.reason = (
                    f"{len(passed)} 个单星候选通过；{evidence_count} 历元相对似然比达到 "
                    f"{self.config.fde_likelihood_ratio:g}:1，当前残差与几何检验通过且无强反证；"
                    f"当前历元独立重算，保留 {diagnosed.dof} 个验证自由度（非完好性保证）"
                )
            _, residuals, azimuths, elevations = self._linearize(
                observations, best.state, epoch.gps_sow
            )
            for i in indices:
                diagnosed.diagnostics.append(
                    SatelliteDiagnostic(
                        observations[i].sat_id,
                        float(residuals[i]),
                        float(residuals[i] / self._sigma),
                        math.degrees(float(elevations[i])),
                        math.degrees(float(azimuths[i])),
                        weight=0.0,
                        excluded=True,
                    )
                )
            if proposal_weights is not None:
                by_id = {
                    o.sat_id: float(w) for o, w in zip(observations, proposal_weights, strict=True)
                }
                for diagnostic in diagnosed.diagnostics:
                    diagnostic.robust_weight = by_id[diagnostic.sat_id]
            diagnosed.diagnostics.sort(key=lambda diagnostic: diagnostic.sat_id)
            return diagnosed
        result.reason = "一星及两星假设均未获得唯一一致解；可能存在更多故障或模型失配"
        if proposal_weights is not None:
            by_id = {
                o.sat_id: float(w) for o, w in zip(observations, proposal_weights, strict=True)
            }
            for diagnostic in result.diagnostics:
                diagnostic.robust_weight = by_id[diagnostic.sat_id]
        return result
