"""A conditional proposal must not become a confidence or receiver-state prior."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from gnss_workbench.cli import app
from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.io import navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT

INPUT = Path(__file__).parent / "data/coherent_proposal.jsonl"


@pytest.mark.parametrize("enabled", [False, True])
def test_experimental_proposals_require_explicit_opt_in_and_are_recorded(tmp_path, enabled):
    assert SolverConfig().coherent_proposals is False
    arguments = ["solve", "--input", str(INPUT), "--out", str(tmp_path)]
    if enabled:
        arguments.append("--enable-coherent-proposals")
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["configuration"]["coherent_proposals"] is enabled
    row = json.loads((tmp_path / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()[44])[
        "improved"
    ]
    assert row["status"] == "SUSPECT"
    selected = next(c for c in row["candidate_scores"] if c["selected"])
    assert (selected.get("provisional_source") == "coherent_proposal") is enabled


def content(solution):
    return {k: v for k, v in solution.to_dict().items() if k != "processing_ms"}


def test_proposal_refits_current_data_without_promoting_or_feeding_back_identity():
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    old, new = [PositioningEngine(nav, SolverConfig(coherent_proposals=v)) for v in (False, True)]
    changed = []
    for epoch in read_epochs(INPUT):
        (a, before), (b, after) = old.solve(epoch), new.solve(epoch)
        assert content(a) == content(b)
        assert np.array_equal(old._initial, new._initial)
        assert before.status == after.status
        for x, y in zip(old._ambiguity.samples, new._ambiguity.samples, strict=True):
            assert x.time_s == y.time_s and np.array_equal(x.statistics, y.statistics)
            assert x.biases == y.biases
        if before.status == "FAULT_EXCLUDED":
            assert content(before) == content(after)
        if before.excluded_sats != after.excluded_sats:
            changed.append(epoch.epoch_id)
            assert before.status == after.status == "SUSPECT"
            assert after.n_used == len(epoch.observations) - 1 >= 5
            assert after.test_statistic <= after.test_threshold
            assert after.pdop <= new.config.pdop_warning
            selected = next(c for c in after.candidate_scores if c["selected"])
            assert selected["selection_method"] == "provisional_likelihood"
            assert selected["provisional_source"] == "coherent_proposal"
            assert selected["selection_log_ratio"] >= selected["required_log_ratio"]
            assert selected["temporal_passed"] and selected["passed"]
    assert changed == [44]
    # Neither retained evidence nor the previous fix can manufacture observations.
    _, invalid = new.solve(
        replace(epoch, epoch_id=epoch.epoch_id + 1, gps_sow=epoch.gps_sow + 1, observations=())
    )
    assert invalid.status == "NO_OBSERVATIONS" and not invalid.has_position
    assert not new._ambiguity.samples and not new._temporal.samples


@pytest.mark.parametrize("rejection", ["current_gate", "prediction_gate", "relative_evidence"])
def test_unconfirmed_history_cannot_bypass_independent_gates(monkeypatch, rejection):
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    old, new = [PositioningEngine(nav, SolverConfig(coherent_proposals=v)) for v in (False, True)]
    epochs = list(read_epochs(INPUT))[:45]
    for epoch in epochs[:-1]:
        old.solve(epoch)
        new.solve(epoch)
    if rejection == "current_gate":
        # Invalidate this current subset independently of its historical score.
        fit = new._fit

        def reject_candidate(observations, sow, initial, *args, **kwargs):
            result = fit(observations, sow, initial, *args, **kwargs)
            if len(observations) == 5 and "G20" not in {o.sat_id for o in observations}:
                result.residual = result.residual + 1000
            return result

        monkeypatch.setattr(new, "_fit", reject_candidate)
    else:
        observe = new._temporal.observe

        def reject_temporal(*args, **kwargs):
            result = observe(*args, **kwargs)
            assert result is not None
            if rejection == "prediction_gate":
                result.passing[:] = False
            else:
                result.statistics[:] = 0  # No relative identity support.
            return result

        monkeypatch.setattr(new._temporal, "observe", reject_temporal)
    _, before = old.solve(epochs[-1])
    _, after = new.solve(epochs[-1])
    assert after.excluded_sats == before.excluded_sats
    assert after.status == before.status == "SUSPECT"
