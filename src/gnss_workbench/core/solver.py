"""Equal-weight SPP and conservative, single-fault residual consistency diagnosis.

No dataset names, fault schedules or reference receiver positions enter this module.
The previous fix is only an iteration initial value, never a measurement constraint.
"""

from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import chi2

from .atmosphere import ionosphere, troposphere
from .coordinates import azimuth_elevation, geodetic
from .ephemeris import C, rotate_to_receive, transmit_state
from .models import Epoch, SatelliteDiagnostic, Solution, SolverConfig


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

    def _fit(self, observations: list[PreparedObservation], sow: float, initial: np.ndarray) -> Fit:
        if len(observations) < 4:
            raise SolveError("INVALID_INSUFFICIENT", "参与解算的卫星不足四颗")
        state = initial.copy()
        for _ in range(self.config.max_iterations):
            h, residual, _, _ = self._linearize(observations, state, sow)
            step, _, rank, singular = np.linalg.lstsq(h, residual, rcond=None)
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
        if n < 4:
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
                improved = self._diagnose(epoch, fit, improved)
            else:
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
            status = error.status if isinstance(error, SolveError) else "INVALID_GEOMETRY"
            invalid = Solution(
                epoch.epoch_id, epoch.gps_week, epoch.gps_sow, status, n_used=n, reason=str(error)
            )
            invalid.processing_ms = (time.perf_counter() - started) * 1000
            return invalid, copy.deepcopy(invalid)

    def _diagnose(self, epoch: Epoch, fit: Fit, result: Solution) -> Solution:
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
