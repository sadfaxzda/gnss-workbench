"""Controlled observation-level perturbations, isolated from the positioning engine."""

from dataclasses import replace
from typing import Literal

from pydantic import BaseModel, Field

from .core.models import Epoch


class FaultScenario(BaseModel):
    kind: Literal["none", "satellite_bias", "common_bias", "dropout"] = "none"
    start_epoch: int = Field(default=120, ge=0)
    duration: int = Field(default=60, ge=1, le=100000)
    sat_id: str = Field(default="G19", pattern=r"^G\d{2}$")
    bias_m: float = Field(default=80.0, ge=-1000, le=1000, allow_inf_nan=False)
    ramp: bool = False
    keep_satellites: int = Field(default=3, ge=0, le=8)


def inject(epoch: Epoch, scenario: FaultScenario) -> Epoch:
    """Use only the received epoch; no lookahead and no changes to source files."""
    offset = epoch.epoch_id - scenario.start_epoch
    if scenario.kind == "none" or not 0 <= offset < scenario.duration:
        return epoch
    if scenario.kind == "dropout":
        return replace(epoch, observations=epoch.observations[: scenario.keep_satellites])
    bias = scenario.bias_m * ((offset + 1) / scenario.duration if scenario.ramp else 1)
    observations = tuple(
        replace(o, pseudorange_m=o.pseudorange_m + bias)
        if scenario.kind == "common_bias" or o.sat_id == scenario.sat_id
        else o
        for o in epoch.observations
    )
    return replace(epoch, observations=observations)
