"""Malformed observations must retain their epoch without masquerading as numbers."""

import json

import pytest

from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.io import navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


@pytest.mark.parametrize(
    "field,value",
    [("pseudorange_m", True), ("cn0_dbhz", False), ("sat_id", ["G", "0", "3"])],
)
def test_bad_observation_preserves_epoch_and_recovers(tmp_path, field, value):
    frames = (COURSE_ROOT / "data/D02_sim_clean.jsonl").read_text(encoding="utf-8").splitlines()
    bad = json.loads(frames[2])
    bad["observations"][0][field] = value
    path = tmp_path / "input.jsonl"
    path.write_text("\n".join([frames[0], frames[1], json.dumps(bad), frames[3]]), encoding="utf-8")
    engine = PositioningEngine(navigation_from(COURSE_ROOT / "data/navigation.json"))
    pairs = [engine.solve(epoch) for epoch in read_epochs(path)]
    for index in (0, 1):
        results = [pair[index] for pair in pairs]
        assert [result.epoch_id for result in results] == [0, 1, 2]
        assert [result.status for result in results] == ["VALID", "INVALID_DATA", "VALID"]
        invalid = results[1]
        assert invalid.x_m is invalid.clock_bias_m is invalid.pdop is None


@pytest.mark.parametrize("value", [[], None, 123])
def test_navigation_root_rejected_with_validation_error(tmp_path, value):
    path = tmp_path / "navigation.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        navigation_from(path)
