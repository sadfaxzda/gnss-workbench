"""Acceptance gaps and algorithm safety boundaries, independent of D03 fault windows."""

import csv
import json
from dataclasses import asdict, replace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from gnss_workbench.api import create_app
from gnss_workbench.core.coordinates import local_enu
from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.experiments import FaultScenario, inject
from gnss_workbench.io import csv_row, navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


@pytest.fixture
def data():
    return navigation_from(COURSE_ROOT / "data/navigation.json"), list(
        read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl")
    )


@pytest.mark.parametrize("method", ["single_fde", "consensus", "adaptive_gnc"])
def test_double_fault_and_trace(data, method):
    nav, epochs = data
    epoch = epochs[73]
    for sat, bias in [("G03", 85), ("G20", -90)]:
        epoch = inject(
            epoch,
            FaultScenario(
                kind="satellite_bias", start_epoch=73, duration=1, sat_id=sat, bias_m=bias
            ),
        )
    baseline, result = PositioningEngine(nav, SolverConfig(algorithm=method)).solve(epoch)
    assert baseline.n_used == 8 and baseline.excluded_sats == []
    if method == "single_fde":
        assert result.status == "SUSPECT"
    else:
        assert result.status == "FAULT_EXCLUDED"
        assert result.excluded_sats == ["G03", "G20"]
        assert result.n_used == 6 and result.dof == 2
        assert len(result.candidate_scores) == 36
        assert result.test_statistic < result.test_threshold
        # Course PDOP is based on unweighted retained geometry, including GNC mode.
        retained = replace(
            epoch,
            observations=tuple(
                o for o in epoch.observations if o.sat_id not in result.excluded_sats
            ),
        )
        ordinary, _ = PositioningEngine(nav, SolverConfig(enable_fde=False)).solve(retained)
        assert result.pdop == pytest.approx(ordinary.pdop, abs=1e-5)
    if method == "adaptive_gnc":
        gnc_trace = [t for t in result.algorithm_trace if "depth" in t]
        assert 1 <= len(gnc_trace) <= 54
        assert all(0 <= d.robust_weight <= 1 for d in result.diagnostics)


def test_truncated_search_cannot_claim_unique_solution(data):
    nav, epochs = data
    epoch = inject(
        epochs[73],
        FaultScenario(kind="satellite_bias", start_epoch=73, duration=1, sat_id="G03", bias_m=85),
    )
    _, result = PositioningEngine(nav, SolverConfig(max_hypotheses=1)).solve(epoch)
    assert result.status == "SUSPECT"
    assert not result.search_complete
    assert result.excluded_sats == []


@pytest.mark.parametrize("indices", [(0, 2, 3, 4), (1, 4, 5, 6), (3, 5, 6, 7)])
def test_poor_geometry_overrides_valid_or_four_satellite_state(data, indices):
    nav, epochs = data
    epoch = replace(epochs[0], observations=tuple(epochs[0].observations[i] for i in indices))
    baseline, result = PositioningEngine(nav).solve(epoch)
    assert baseline.status == result.status == "GEOMETRY_WARNING"
    assert result.pdop > 30


def test_rank_deficient_geometry_is_invalid(data):
    nav, epochs = data
    observations = epochs[0].observations
    # Distinct IDs with identical broadcast orbits cannot observe four unknowns.
    for observation in observations:
        nav["ephemerides"][observation.sat_id] = nav["ephemerides"]["G03"].copy()
    epoch = replace(
        epochs[0],
        observations=tuple(
            replace(o, pseudorange_m=observations[0].pseudorange_m) for o in observations
        ),
    )
    baseline, result = PositioningEngine(nav).solve(epoch)
    assert baseline.status == result.status == "INVALID_GEOMETRY"
    assert result.x_m is result.pdop is None


@pytest.mark.parametrize("satellite", ["G03", "G07", "G08", "G11", "G19", "G20", "G24", "G28"])
@pytest.mark.parametrize("sign", [-1, 1])
def test_ramp_teacher_thresholds_all_satellites(data, satellite, sign):
    nav, epochs = data
    with (COURSE_ROOT / "reference/D02_sim_clean_truth.csv").open() as stream:
        truth = list(csv.DictReader(stream))
    engine = PositioningEngine(nav)
    errors, strong, detected = [], 0, 0
    scenario = FaultScenario(
        kind="satellite_bias",
        start_epoch=0,
        duration=40,
        sat_id=satellite,
        bias_m=sign * 100,
        ramp=True,
    )
    for epoch in epochs[:40]:
        _, result = engine.solve(inject(epoch, scenario))
        assert result.has_position
        reference = np.array([float(truth[epoch.epoch_id][key]) for key in ("x_m", "y_m", "z_m")])
        enu = local_enu(np.array([result.x_m, result.y_m, result.z_m]), reference)
        errors.append(np.linalg.norm(enu[:2]))
        if (epoch.epoch_id + 1) * 2.5 >= 30:
            strong += 1
            detected += satellite in result.flagged_sats
    assert np.percentile(errors, 95) <= 10
    assert np.mean(np.array(errors) <= 10) >= 0.95
    assert detected / strong >= 0.9


def test_invalid_observation_retains_identity_and_recovers(data, tmp_path):
    nav, epochs = data
    frames = [{"type": "epoch", **asdict(e)} for e in epochs[:3]]
    frames[1]["observations"][0]["pseudorange_m"] = -1
    source = tmp_path / "input.jsonl"
    source.write_text("\n".join(json.dumps(f) for f in frames))
    engine = PositioningEngine(nav)
    results = [engine.solve(epoch)[1] for epoch in read_epochs(source)]
    assert [r.epoch_id for r in results] == [0, 1, 2]
    assert [r.status for r in results] == ["VALID", "INVALID_DATA", "VALID"]
    assert all(
        csv_row(results[1])[key] is None
        for key in ("x_m", "y_m", "z_m", "clock_bias_m", "pdop", "residual_rms_m")
    )


def test_import_persist_validate_run_and_export(data, tmp_path):
    from test_api import wait_completed

    nav, epochs = data
    frames = [{"type": "epoch", **asdict(e)} for e in epochs[:3]]
    frames[1]["observations"][0]["pseudorange_m"] = -1
    jsonl = "\n".join(json.dumps(frame) for frame in frames)
    with TestClient(create_app(tmp_path)) as client:
        imported = client.post(
            "/api/datasets", json={"name": "未知测试.jsonl", "jsonl": jsonl, "navigation": nav}
        )
        assert imported.status_code == 201, imported.text
        dataset_id = imported.json()["id"]
        run_id = client.post(
            "/api/runs", json={"dataset_id": dataset_id, "interval_seconds": 0}
        ).json()["id"]
        info = wait_completed(client, run_id)
        assert info["status"] == "completed"
        assert client.get(f"/api/runs/{run_id}/download/navigation.json").json() == nav
        assert info["summary"]["evaluation"] is None
        history = client.get(f"/api/runs/{run_id}/epochs").json()
        assert [e["improved"]["status"] for e in history] == ["VALID", "INVALID_DATA", "VALID"]
        replay = client.get(f"/api/runs/{run_id}/download/input.jsonl").text
        assert json.loads(replay.splitlines()[0])["type"] == "meta"
        assert json.loads(replay.splitlines()[2])["observations"][0]["pseudorange_m"] == -1
        assert (
            client.post(
                "/api/datasets", json={"name": "重复编号", "jsonl": jsonl + "\n" + jsonl}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/datasets", json={"name": "空数据", "jsonl": '{"type":"meta"}'}
            ).status_code
            == 422
        )
        assert (
            client.post("/api/datasets", json={"name": "非对象", "jsonl": "[]"}).status_code == 422
        )
        nav["ephemerides"]["G03"]["e"] = 2
        assert (
            client.post(
                "/api/datasets", json={"name": "无效星历", "jsonl": jsonl, "navigation": nav}
            ).status_code
            == 422
        )
        assert client.post("/api/runs", json={"dataset_id": "../secret"}).status_code == 422
        assert (
            client.post("/api/runs", json={"dataset_id": "custom_nonexistent"}).status_code == 409
        )
    with TestClient(create_app(tmp_path)) as client:
        assert dataset_id in {d["id"] for d in client.get("/api/datasets").json()}
