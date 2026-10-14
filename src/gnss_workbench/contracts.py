"""Versioned application contract. OpenAPI generates the web client's types."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .core.models import Solution
from .experiments import FaultScenario


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str = Field(default="D03_sim_demo", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    source: Literal["file", "tcp"] = "file"
    interval_seconds: float = Field(default=0.03, ge=0, le=30, allow_inf_nan=False)
    tcp_port: int = Field(default=8765, ge=1024, le=65535)
    enable_fde: bool = True
    algorithm: Literal["single_fde", "consensus", "adaptive_gnc"] = "consensus"
    noise_sigma_m: float = Field(default=1.0, ge=0.1, le=20, allow_inf_nan=False)
    false_alarm_probability: float = Field(default=0.001, gt=0, lt=0.1, allow_inf_nan=False)
    scenario: FaultScenario = Field(default_factory=FaultScenario)

    @model_validator(mode="after")
    def scenario_scope(self) -> "RunRequest":
        if self.scenario.kind != "none" and (
            self.source != "file" or self.dataset_id != "D02_sim_clean"
        ):
            raise ValueError("Controlled fault experiments use D02_sim_clean file input")
        return self


class DatasetInfo(BaseModel):
    id: str
    title: str
    kind: str
    epochs: int
    description: str


class RunInfo(BaseModel):
    id: str
    created_at: str
    status: str
    configuration: RunRequest
    epoch_count: int
    summary: dict[str, Any]
    error: str | None


class HealthInfo(BaseModel):
    status: str
    version: str
    schema_version: Literal["gnss-stream/1"] = "gnss-stream/1"


class EpochView(BaseModel):
    baseline_enu: list[float] | None
    improved_enu: list[float] | None
    latitude_deg: float | None
    longitude_deg: float | None
    height_m: float | None
    correction_m: float | None


class EpochFrame(BaseModel):
    type: Literal["epoch"] = "epoch"
    epoch_id: int
    baseline: Solution
    improved: Solution
    view: EpochView


class DatasetImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    jsonl: str = Field(min_length=1, max_length=16 * 1024 * 1024)
    navigation: dict[str, Any] | None = None
