from dataclasses import replace

import numpy as np
import pytest

from gnss_workbench.core.ephemeris import C, satellite_state
from gnss_workbench.core.models import Epoch, SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.experiments import FaultScenario, inject
from gnss_workbench.io import export_solutions, navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


@pytest.fixture
def navigation():
    return navigation_from(COURSE_ROOT / "data/navigation.json")


@pytest.fixture
def clean():
    return list(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))


def test_all_broadcast_checkpoints(navigation):
    import csv

    with (COURSE_ROOT / "reference/satellite_checkpoints.csv").open() as stream:
        for row in csv.DictReader(stream):
            xyz, clock = satellite_state(
                navigation["ephemerides"][row["sat_id"]], float(row["gps_sow_tx"])
            )
            assert (
                np.linalg.norm(xyz - [float(row[k]) for k in ["x_tx_m", "y_tx_m", "z_tx_m"]]) < 1e-4
            )
            assert abs(clock - float(row["system_clock_s"])) * C < 1e-5


@pytest.mark.parametrize(
    "n,status", [(0, "NO_OBSERVATIONS"), (3, "INVALID_INSUFFICIENT"), (4, "NO_REDUNDANCY")]
)
def test_observability_not_bypassed_by_previous_fix(navigation, clean, n, status):
    engine = PositioningEngine(navigation)
    engine.solve(clean[0])
    baseline, improved = engine.solve(replace(clean[1], observations=clean[1].observations[:n]))
    assert baseline.status == improved.status == status
    if n < 4:
        assert improved.x_m is improved.clock_bias_m is improved.pdop is None


@pytest.mark.parametrize("satellite,bias", [("G03", 65), ("G08", -90), ("G20", 110), ("G28", 50)])
def test_unseen_fault_satellites_and_signs(navigation, clean, satellite, bias):
    epoch = clean[73]
    altered = inject(
        epoch,
        FaultScenario(
            kind="satellite_bias", start_epoch=73, duration=1, sat_id=satellite, bias_m=bias
        ),
    )
    baseline, improved = PositioningEngine(navigation).solve(altered)
    assert improved.excluded_sats == [satellite]
    assert improved.status == "FAULT_EXCLUDED"
    assert len(improved.candidate_scores) == 8
    assert epoch.observations != altered.observations
    assert baseline.n_used == 8 and improved.n_used == 7


def test_common_bias_is_clock_change(navigation, clean):
    _, original = PositioningEngine(navigation).solve(clean[46])
    altered = inject(
        clean[46], FaultScenario(kind="common_bias", start_epoch=46, duration=1, bias_m=135)
    )
    _, shifted = PositioningEngine(navigation).solve(altered)
    assert shifted.flagged_sats == []
    assert abs(shifted.clock_bias_m - original.clock_bias_m - 135) < 0.01
    assert (
        np.linalg.norm(
            np.array([shifted.x_m, shifted.y_m, shifted.z_m])
            - [original.x_m, original.y_m, original.z_m]
        )
        < 0.01
    )


def test_ablation_is_same_solution(navigation, clean):
    epoch = inject(clean[99], FaultScenario(kind="satellite_bias", start_epoch=99, duration=1))
    baseline, improved = PositioningEngine(navigation, SolverConfig(enable_fde=False)).solve(epoch)
    assert [baseline.x_m, baseline.y_m, baseline.z_m] == [improved.x_m, improved.y_m, improved.z_m]
    assert improved.excluded_sats == []


def test_aged_ephemeris_and_duplicate_satellite(navigation, clean):
    _, result = PositioningEngine(navigation).solve(replace(clean[0], gps_week=1317))
    assert result.status == "INVALID_EPHEMERIS"
    from dataclasses import asdict

    raw = {"type": "epoch", **asdict(clean[0])}
    raw["observations"] = [asdict(clean[0].observations[0])] * 4
    with pytest.raises(ValueError, match="Duplicate"):
        Epoch.from_dict(raw)


@pytest.mark.parametrize("dataset", ["D02_sim_clean", "D03_sim_demo"])
def test_course_metrics_and_csv_contract(navigation, tmp_path, dataset):
    from gnss_workbench.evaluation import evaluate_run

    engine = PositioningEngine(navigation)
    pairs = [engine.solve(e) for e in read_epochs(COURSE_ROOT / "data" / f"{dataset}.jsonl")]
    export_solutions(tmp_path / "baseline.csv", [p[0] for p in pairs])
    export_solutions(tmp_path / "improved.csv", [p[1] for p in pairs])
    metrics = evaluate_run(
        COURSE_ROOT / "data" / f"{dataset}.jsonl",
        COURSE_ROOT / "reference" / f"{dataset}_truth.csv",
        tmp_path,
    )["improved"]
    assert metrics["contract_violation_count"] == 0
    assert metrics["h_p95_m"] < 5
    assert metrics["availability_on_required"] == 1
    assert metrics["false_alarm_epoch_rate"] <= 0.05
    if dataset == "D03_sim_demo":
        assert metrics["fault_detection_recall"] >= 0.9
        assert metrics["correct_invalid_state_rate"] == 1
        assert metrics["correct_no_redundancy_rate"] == 1


def test_real_data_no_claim_of_absolute_truth(navigation):
    engine = PositioningEngine(navigation)
    epochs = list(read_epochs(COURSE_ROOT / "data/D01_real_excerpt.jsonl"))
    assert len(epochs) == 20
    results = [engine.solve(epoch)[0] for epoch in epochs]
    assert all(result.has_position for result in results)
    assert results[-1].gps_sow == epochs[-1].gps_sow
