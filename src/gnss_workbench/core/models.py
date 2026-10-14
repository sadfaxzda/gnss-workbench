"""Explicit units and validity states shared by batch and streaming solvers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class Observation:
    sat_id: str
    pseudorange_m: float
    cn0_dbhz: float | None = None


@dataclass(frozen=True)
class Epoch:
    epoch_id: int
    gps_week: int
    gps_sow: float
    observations: tuple[Observation, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Epoch:
        if data.get("type") != "epoch":
            raise ValueError("Expected an epoch frame")
        eid, week, sow = data["epoch_id"], data["gps_week"], data["gps_sow"]
        if isinstance(eid, bool) or not isinstance(eid, int) or eid < 0:
            raise ValueError("epoch_id must be a nonnegative integer")
        if isinstance(week, bool) or not isinstance(week, int) or week < 0:
            raise ValueError("gps_week must be a nonnegative integer")
        if not isfinite(float(sow)) or not 0 <= float(sow) < 604800:
            raise ValueError("gps_sow must be a finite GPS week second")
        obs = tuple(Observation(**o) for o in data["observations"])
        if len({o.sat_id for o in obs}) != len(obs):
            raise ValueError("Duplicate satellite observations")
        for o in obs:
            if len(o.sat_id) != 3 or o.sat_id[0] != "G" or not o.sat_id[1:].isdigit():
                raise ValueError("Only Gxx GPS satellite identifiers are supported")
            if not isfinite(o.pseudorange_m) or o.pseudorange_m <= 0:
                raise ValueError("Pseudorange must be finite and positive")
            if o.cn0_dbhz is not None and not isfinite(o.cn0_dbhz):
                raise ValueError("C/N0 must be finite or null")
        return cls(eid, week, float(sow), obs)


@dataclass(frozen=True)
class SolverConfig:
    noise_sigma_m: float = 1.0
    false_alarm_probability: float = 0.001
    max_iterations: int = 20
    convergence_m: float = 0.0001
    elevation_mask_deg: float = 3.0
    pdop_warning: float = 30.0
    enable_fde: bool = True

    def __post_init__(self) -> None:
        if not isfinite(self.noise_sigma_m) or self.noise_sigma_m <= 0:
            raise ValueError("noise_sigma_m must be positive")
        if not 0 < self.false_alarm_probability < 0.1:
            raise ValueError("false_alarm_probability must be in (0, 0.1)")


@dataclass
class SatelliteDiagnostic:
    sat_id: str
    residual_m: float
    normalized_residual: float
    elevation_deg: float
    azimuth_deg: float
    weight: float = 1.0
    excluded: bool = False


@dataclass
class Solution:
    epoch_id: int
    gps_week: int
    gps_sow: float
    status: str
    x_m: float | None = None
    y_m: float | None = None
    z_m: float | None = None
    clock_bias_m: float | None = None
    n_used: int = 0
    pdop: float | None = None
    flagged_sats: list[str] = field(default_factory=list)
    excluded_sats: list[str] = field(default_factory=list)
    residual_rms_m: float | None = None
    processing_ms: float = 0.0
    diagnostics: list[SatelliteDiagnostic] = field(default_factory=list)
    reason: str = ""
    test_statistic: float | None = None
    test_threshold: float | None = None
    dof: int = 0
    candidate_scores: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_position(self) -> bool:
        return self.x_m is not None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CSV_FIELDS = [
    "epoch_id",
    "gps_week",
    "gps_sow",
    "status",
    "x_m",
    "y_m",
    "z_m",
    "clock_bias_m",
    "n_used",
    "pdop",
    "flagged_sats",
    "excluded_sats",
    "residual_rms_m",
    "processing_ms",
]
