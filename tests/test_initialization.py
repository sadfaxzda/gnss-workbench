"""Independent squared-range construction and improved-only recovery boundary."""

from dataclasses import replace

import numpy as np
import pytest

from gnss_workbench.core.initialization import algebraic_seeds
from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.solver import PositioningEngine, SolveError
from gnss_workbench.io import navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


@pytest.mark.parametrize("n", [4, 5, 6, 7, 8])
def test_algebraic_seeds_recover_arbitrary_position_and_signed_clock(n):
    rng = np.random.default_rng(640020 + n)
    for _ in range(20):
        satellite = rng.normal(size=(n, 3))
        satellite *= 2.65e7 / np.linalg.norm(satellite, axis=1)[:, None]
        receiver = rng.normal(size=3)
        receiver *= rng.uniform(6.3e6, 6.5e6) / np.linalg.norm(receiver)
        clock = rng.uniform(-2e5, 2e5)
        ranges = np.linalg.norm(satellite - receiver, axis=1) + clock
        seeds = algebraic_seeds(satellite, ranges)
        truth = np.append(receiver, clock)
        assert min(np.linalg.norm(seed - truth) for seed in seeds) < 1e-4


def test_rank_deficiency_has_no_fabricated_seed():
    satellite = np.tile([2.65e7, 0, 0], (4, 1))
    assert algebraic_seeds(satellite, np.full(4, 2e7)) == []
    assert algebraic_seeds(satellite[:3], np.full(3, 2e7)) == []


@pytest.mark.parametrize("recovery", [False, True])
def test_failed_ordinary_fit_is_unchanged_when_improved_recovers(monkeypatch, recovery):
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    epoch = next(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))
    epoch = replace(epoch, observations=epoch.observations[:4])
    engine = PositioningEngine(nav, SolverConfig(algebraic_recovery=recovery))
    original = engine._fit
    calls = 0

    def initial_failure(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SolveError("INVALID_CONVERGENCE", "synthetic initial iterate failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(engine, "_fit", initial_failure)
    baseline, improved = engine.solve(epoch)
    assert baseline.status == "INVALID_CONVERGENCE" and not baseline.has_position
    assert baseline.reason == "synthetic initial iterate failure"
    assert engine._initial == pytest.approx(np.zeros(4))
    if recovery:
        assert improved.status == "NO_REDUNDANCY" and improved.n_used == 4
        reference = original(engine._prepare(epoch), epoch.gps_sow, np.zeros(4))
        assert improved.x_m == pytest.approx(reference.state[0], abs=1e-5)
        assert improved.clock_bias_m == pytest.approx(reference.state[3], abs=1e-5)
        assert improved.flagged_sats == improved.excluded_sats == []
    else:
        assert improved.status == baseline.status and not improved.has_position
        assert calls == 1


def test_recovery_never_bypasses_insufficient_observations(monkeypatch):
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    epoch = next(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))
    engine = PositioningEngine(nav)

    def forbidden(*args):
        pytest.fail("Must not recover fewer than four measurements")

    monkeypatch.setattr(engine, "_recover_convergence", forbidden)
    for n in (0, 1, 2, 3):
        b, s = engine.solve(replace(epoch, observations=epoch.observations[:n]))
        assert b.status == s.status and not b.has_position and not s.has_position


def test_nearly_constant_elevation_geometry_is_diagnosed_even_for_complex_roots(monkeypatch):
    from gnss_workbench.core.initialization import algebraic_candidates
    from gnss_workbench.core.models import Epoch, Observation
    from gnss_workbench.core.solver import PreparedObservation

    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    rng = np.random.default_rng(650102)
    receiver = np.array([6378137.0, 0, 0])
    complex_cases = 0
    for _ in range(20):
        az, el = rng.uniform(0, 2 * np.pi, 4), rng.uniform(0.7, 0.7001, 4)
        los = np.column_stack((np.sin(el), np.cos(el) * np.cos(az), np.cos(el) * np.sin(az)))
        # Independent true geometry proves this is a poor-geometry test.
        h = np.column_stack((-los, np.ones(4)))
        assert np.linalg.norm(np.linalg.pinv(h)[:3]) > 30
        distances = rng.uniform(2e7, 2.4e7, 4)
        satellite = receiver + los * distances[:, None]
        ranges = distances + 50000 + rng.normal(0, 30, 4)
        candidates = algebraic_candidates(satellite, ranges)
        complex_cases += any(not c.real_root for c in candidates)
        obs = tuple(Observation(f"G{i + 1:02}", float(p)) for i, p in enumerate(ranges))
        prepared = [
            PreparedObservation(o.sat_id, o.pseudorange_m, s, 0.0)
            for o, s in zip(obs, satellite, strict=True)
        ]
        outputs = []
        for enabled in (False, True):
            engine = PositioningEngine(nav, SolverConfig(complete_geometry_diagnosis=enabled))
            monkeypatch.setattr(engine, "_prepare", lambda epoch, prepared=prepared: prepared)
            outputs.append(engine.solve(Epoch(0, 1316, 518400, obs)))
        old, new = outputs
        for field in ["status", "x_m", "y_m", "z_m", "clock_bias_m", "pdop"]:
            assert getattr(old[0], field) == getattr(new[0], field)
        assert new[1].status in {"GEOMETRY_WARNING", "INVALID_GEOMETRY"}
        if new[1].status == "INVALID_GEOMETRY":
            assert not new[1].has_position and new[1].pdop is None
    assert complex_cases > 0


def test_extreme_finite_pseudoranges_cannot_overflow_recovery():
    from gnss_workbench.core.initialization import algebraic_candidates

    satellite = np.array([[2e7, 1e7, 2e7], [-2e7, 1e7, 2e7], [2e7, -1e7, 2e7], [-2e7, -1e7, 2e7]])
    assert algebraic_candidates(satellite, np.full(4, 1e307)) == []
    assert algebraic_candidates(np.empty((0, 3)), np.empty(0)) == []


def test_failed_healthy_geometry_is_not_relabelled_as_bad_geometry():
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    epoch = next(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))
    baseline, improved = PositioningEngine(nav, SolverConfig(max_iterations=1)).solve(epoch)
    assert baseline.status == improved.status == "INVALID_CONVERGENCE"
    assert not improved.has_position
