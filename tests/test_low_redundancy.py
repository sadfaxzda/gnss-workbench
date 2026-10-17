"""Numerical evidence, causal reset rules, and unchanged course contracts."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from gnss_workbench.core.coordinates import local_enu
from gnss_workbench.core.diagnosis import AmbiguityResolver
from gnss_workbench.core.models import CSV_FIELDS, SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.io import csv_row, navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


@pytest.fixture(scope="module")
def data():
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    epochs = list(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))
    with (COURSE_ROOT / "reference/D02_sim_clean_truth.csv").open() as stream:
        truth = list(csv.DictReader(stream))
    return nav, epochs, truth


def biased(epoch, n, satellite, bias):
    return replace(
        epoch,
        observations=tuple(
            replace(o, pseudorange_m=o.pseudorange_m + (bias if o.sat_id == satellite else 0))
            for o in epoch.observations[:n]
        ),
    )


def test_likelihood_uses_all_alternatives_and_accumulates_without_coordinates():
    resolver = AmbiguityResolver(8, 5, 20)
    first = resolver.observe(100, ("A", "B", "C"), {"A": 0, "B": 2, "C": 20})
    assert first.selected is None
    for t in range(101, 105):
        decision = resolver.observe(t, ("C", "A", "B"), {"C": 20, "B": 2, "A": 0})
    assert decision.selected == "A"
    assert decision.method == "causal_likelihood"
    assert decision.epochs == 5 and decision.start_time == 100
    assert decision.log_ratio >= np.log(20)


@pytest.mark.parametrize(
    "time,satellites", [(99, ("A", "B")), (103, ("A", "B")), (110, ("A", "B")), (104, ("A", "C"))]
)
def test_nonincreasing_time_gap_or_changed_observations_discards_history(time, satellites):
    resolver = AmbiguityResolver(8, 5, 20)
    for t in range(100, 104):
        resolver.observe(t, ("A", "B"), {"A": 0, "B": 2})
    decision = resolver.observe(time, satellites, {"A": 0, "B": 2})
    assert decision.selected is None
    assert decision.epochs == 1


def test_history_cannot_override_strong_current_evidence_or_force_a_tie():
    resolver = AmbiguityResolver(8, 5, 20)
    for t in range(8):
        resolver.observe(t, ("A", "B"), {"A": 0, "B": 2})
    assert resolver.observe(8, ("A", "B"), {"A": 1, "B": 0}).selected == "A"
    changed = resolver.observe(9, ("A", "B"), {"A": 30, "B": 0})
    assert changed.selected == "B" and changed.epochs == 1
    resolver.reset()
    for t in range(20):
        decision = resolver.observe(t, ("A", "B"), {"A": 0, "B": 0})
        assert decision.selected is None
    assert decision.epochs == 8


def test_rejected_previous_identity_cannot_transfer_old_evidence_to_other_candidates():
    resolver = AmbiguityResolver(16, 5, 20)
    for t in range(16):
        resolver.observe(t, ("A", "B", "C"), {"A": 0, "B": 100, "C": 110}, {"A"})
    # A is now impossible, while B and C are indistinguishable. Previous epochs
    # must not make B look certain solely because it fitted the old A fault less badly.
    changed = resolver.observe(16, ("A", "B", "C"), {"A": 100, "B": 2, "C": 2}, {"B", "C"})
    assert changed.epochs == 1 and changed.selected is None
    assert changed.window_shares["B"] == changed.window_shares["C"]


def test_seven_satellite_ambiguous_case_has_explicit_evidence_and_same_ols(data):
    nav, epochs, _ = data
    epoch = biased(epochs[73], 7, "G07", -30)
    ordinary, before = PositioningEngine(nav, SolverConfig(resolve_ambiguity=False)).solve(epoch)
    baseline, improved = PositioningEngine(nav).solve(epoch)
    assert before.status == "SUSPECT"
    assert improved.status == "FAULT_EXCLUDED" and improved.excluded_sats == ["G07"]
    assert sum(c["passed"] for c in improved.candidate_scores) == 2
    chosen = next(c for c in improved.candidate_scores if c.get("selected"))
    assert chosen["selection_log_ratio"] >= chosen["required_log_ratio"]
    for key in ["x_m", "y_m", "z_m", "clock_bias_m", "pdop", "residual_rms_m"]:
        assert getattr(baseline, key) == getattr(ordinary, key)
    assert list(csv_row(improved)) == CSV_FIELDS
    assert improved.n_used == 6
    retained = replace(
        epoch, observations=tuple(o for o in epoch.observations if o.sat_id != "G07")
    )
    fitted, _ = PositioningEngine(nav, SolverConfig(enable_fde=False)).solve(retained)
    assert improved.pdop == pytest.approx(fitted.pdop, abs=1e-5)
    json.dumps(improved.to_dict(), allow_nan=False)


def test_smallest_residual_is_not_automatically_excluded(data):
    nav, epochs, _ = data
    _, solution = PositioningEngine(nav, SolverConfig(provisional_fde=False)).solve(
        biased(epochs[0], 6, "G07", -30)
    )
    assert solution.status == "SUSPECT" and not solution.excluded_sats
    best = min(solution.candidate_scores, key=lambda candidate: candidate["statistic"])
    assert best["sat_id"] == "G20"  # Wrong minimum in the original audit counterexample.


def test_provisional_fit_does_not_claim_confirmed_identity_in_known_wrong_minimum(data):
    nav, epochs, _ = data
    epoch = biased(epochs[0], 6, "G07", -30)
    baseline, provisional = PositioningEngine(nav).solve(epoch)
    ordinary, conservative = PositioningEngine(nav, SolverConfig(provisional_fde=False)).solve(
        epoch
    )
    assert baseline.x_m == ordinary.x_m
    assert provisional.status == conservative.status == "SUSPECT"
    assert provisional.flagged_sats == provisional.excluded_sats == ["G20"]
    assert provisional.n_used == 5 and provisional.dof == 1
    selected = next(c for c in provisional.candidate_scores if c.get("selected"))
    assert selected["selection_method"] == "provisional_likelihood" and selected["passed"]
    assert "身份尚未确认" in provisional.reason
    # This is deliberately a WRONG tentative identity: do not hide this tradeoff
    # by reporting all flags as confirmed diagnoses or flagging every candidate.
    retained = replace(
        epoch, observations=tuple(o for o in epoch.observations if o.sat_id != "G20")
    )
    independent, _ = PositioningEngine(nav, SolverConfig(enable_fde=False)).solve(retained)
    assert provisional.x_m == pytest.approx(independent.x_m, abs=1e-5)
    assert provisional.pdop == pytest.approx(independent.pdop, abs=1e-5)
    assert selected["candidate_horizontal_separation_m"] == 0
    alternative = next(c for c in provisional.candidate_scores if c["sat_id"] == "G07")
    independent_alternative, _ = PositioningEngine(nav, SolverConfig(enable_fde=False)).solve(
        replace(epoch, observations=tuple(o for o in epoch.observations if o.sat_id != "G07"))
    )

    def xyz(solution):
        return np.array([solution.x_m, solution.y_m, solution.z_m])

    expected = np.linalg.norm(local_enu(xyz(independent_alternative), xyz(provisional))[:2])
    assert alternative["candidate_horizontal_separation_m"] == pytest.approx(expected, abs=1e-5)
    assert expected > 10  # Passing residuals can correspond to widely separated fixes.


def test_unique_passing_subset_still_needs_relative_identity_evidence(data):
    nav, _, _ = data
    epoch = next(read_epochs(Path(__file__).parent / "data/weak_unique_subset.jsonl"))
    _, old = PositioningEngine(nav, SolverConfig(strict_fde_confirmation=False)).solve(epoch)
    baseline, new = PositioningEngine(nav).solve(epoch)
    assert old.status == "FAULT_EXCLUDED"
    assert new.status == "SUSPECT"
    assert sum(c["passed"] for c in new.candidate_scores) == 1
    assert old.excluded_sats == new.excluded_sats == ["G07"]
    assert new.x_m == old.x_m and baseline.n_used == 6
    selected = next(c for c in new.candidate_scores if c.get("selected"))
    assert selected["selection_log_ratio"] < selected["required_log_ratio"]
    assert selected["selection_method"] == "provisional_likelihood"
    assert selected["provisional_source"] == "unique_passing"
    for c in new.candidate_scores:
        assert c["nearest_fault_alternative"] != c["sat_id"]
        assert 0 <= c["fault_direction_correlation"] <= 1
        assert 0 <= c["fault_direction_angle_deg"] <= 90
    _, conservative = PositioningEngine(nav, SolverConfig(provisional_fde=False)).solve(epoch)
    assert conservative.status == "SUSPECT" and not conservative.excluded_sats


def test_weak_history_can_select_tentative_fit_without_certifying_it():
    resolver = AmbiguityResolver(16, 5, 20)
    resolver.observe(1, ("A", "B", "C"), {"A": 0, "B": 2, "C": 50})
    decision = resolver.observe(
        2,
        ("A", "B", "C"),
        {"A": 0.4, "B": 0, "C": 50},
        {"A", "B"},
        require_current_agreement=True,
        use_unconfirmed_history=True,
    )
    assert decision.current_shares["B"] > decision.current_shares["A"]
    assert decision.window_shares["A"] > decision.window_shares["B"]
    assert decision.log_ratio < np.log(20) and decision.selected is None
    assert decision.tentative == "A" and decision.tentative_source == "unconfirmed_history"
    # A rejected previous identity cannot carry this weak evidence into a switch.
    changed = resolver.observe(
        3,
        ("A", "B", "C"),
        {"A": 12, "B": 0, "C": 1},
        {"B", "C"},
        use_unconfirmed_history=True,
    )
    assert changed.epochs == 1 and changed.selected is None
    assert changed.tentative == "B" and changed.tentative_source == "current"


def test_tentative_history_does_not_override_strong_current_contradiction():
    resolver = AmbiguityResolver(16, 5, 20)
    for t in range(8):
        resolver.observe(t, ("A", "B", "C"), {"A": 0, "B": 1, "C": 2})
    changed = resolver.observe(
        8,
        ("A", "B", "C"),
        {"A": 7, "B": 0, "C": 0.1},
        {"A", "B", "C"},
        use_unconfirmed_history=True,
    )
    assert changed.selected is None and changed.tentative == "B"


def test_signed_fault_innovation_detects_change_even_when_old_residual_still_passes():
    resolver = AmbiguityResolver(16, 5, 20)
    values = {"A": 0.2, "B": 2.2, "C": 20}
    biases = {"A": (30.0, 2.0), "B": (-40.0, 4.0), "C": (5.0, 1.0)}
    for t in range(8):
        resolver.observe(t, tuple(values), values, {"A", "B"}, biases, 13.8155)
    same = resolver.observe(8, tuple(values), values, {"A", "B"}, biases, 13.8155)
    assert same.selected == "A" and same.epochs == 9
    changed = resolver.observe(
        9, tuple(values), values, {"A", "B"}, {**biases, "A": (-30.0, 2.0)}, 13.8155
    )
    assert changed.reset_reason == "fault_amplitude_change"
    assert changed.innovation_statistic == pytest.approx(900.2)
    assert changed.innovation_satellite == "A"
    assert changed.epochs == 1 and changed.selected is None


def test_fault_innovation_accounts_for_geometry_uncertainty():
    resolver = AmbiguityResolver(16, 5, 20)
    values = {"A": 0.2, "B": 2.2}
    for t in range(5):
        resolver.observe(
            t, tuple(values), values, set(values), {"A": (30, 1000), "B": (0, 1)}, 13.8
        )
    uncertain = resolver.observe(
        5, tuple(values), values, set(values), {"A": (-30, 1000), "B": (0, 1)}, 13.8
    )
    assert uncertain.epochs == 6 and uncertain.reset_reason is None
    assert uncertain.innovation_statistic == pytest.approx(2.0)


def test_strict_confirmation_does_not_certify_history_when_current_best_disagrees():
    resolver = AmbiguityResolver(16, 5, 20)
    for t in range(8):
        resolver.observe(t, ("A", "B"), {"A": 0, "B": 2}, require_current_agreement=True)
    decision = resolver.observe(8, ("A", "B"), {"A": 1, "B": 0}, require_current_agreement=True)
    assert decision.selected is None and decision.window_shares["A"] > 0.95
    assert decision.current_shares["B"] > decision.current_shares["A"]


@pytest.mark.parametrize("n", [6, 7])
def test_persistent_single_fault_improves_without_constraining_receiver(data, n):
    nav, epochs, truth = data
    results = {}
    for enabled in [False, True]:
        errors, detected, wrong, total = [], 0, 0, 0
        for satellite in [o.sat_id for o in epochs[0].observations[:n]]:
            for sign in [-1, 1]:
                engine = PositioningEngine(nav, SolverConfig(resolve_ambiguity=enabled))
                for t in range(80):
                    fault = 10 <= t < 70
                    epoch = biased(epochs[t], n, satellite, sign * 30 if fault else 0)
                    baseline, solution = engine.solve(epoch)
                    if not fault:
                        assert solution.status == "VALID" and not solution.flagged_sats
                        assert not engine._ambiguity.samples
                        continue
                    assert solution.has_position
                    total += 1
                    detected += satellite in solution.flagged_sats
                    wrong += bool(set(solution.excluded_sats) - {satellite})
                    reference = np.array([float(truth[t][k]) for k in ("x_m", "y_m", "z_m")])
                    errors.append(
                        np.linalg.norm(
                            local_enu(
                                np.array([solution.x_m, solution.y_m, solution.z_m]), reference
                            )[:2]
                        )
                    )
                    assert baseline.n_used == n and not baseline.excluded_sats
        results[enabled] = (
            detected / total,
            wrong / total,
            np.percentile(errors, 95),
            np.mean(np.array(errors) <= 10),
        )
    assert results[True][0] > results[False][0]
    assert results[True][2] < results[False][2]
    assert results[True][1] <= 0.01
    assert results[True][0] >= 0.90
    assert results[True][2] <= 10
    assert results[True][3] >= 0.95


@pytest.mark.parametrize("invalid", ["empty", "three", "four", "bad", "aged"])
def test_invalid_or_unmonitored_epoch_clears_diagnosis_state(data, invalid):
    nav, epochs, _ = data
    engine = PositioningEngine(nav)
    for epoch in epochs[:5]:
        engine.solve(biased(epoch, 6, "G07", -30))
    assert engine._ambiguity.samples
    if invalid == "bad":
        epoch = replace(epochs[5], data_error="broken observation")
    elif invalid == "aged":
        epoch = replace(epochs[5], gps_week=epochs[5].gps_week + 1)
    else:
        epoch = replace(
            epochs[5],
            observations=epochs[5].observations[: {"empty": 0, "three": 3, "four": 4}[invalid]],
        )
    engine.solve(epoch)
    assert not engine._ambiguity.samples


def test_diagnosis_is_causal_and_observation_order_independent(data):
    nav, epochs, _ = data
    left, right = PositioningEngine(nav), PositioningEngine(nav)
    for t in range(20):
        epoch = biased(epochs[t], 6, "G07", -30)
        a = left.solve(epoch)[1]
        b = right.solve(replace(epoch, epoch_id=900 - t, observations=epoch.observations[::-1]))[1]
        assert a.status == b.status and a.excluded_sats == b.excluded_sats
        assert a.x_m == pytest.approx(b.x_m, abs=1e-5)
    # Future changes cannot rewrite the saved prefix; epochs are returned by value.
    saved = json.dumps(a.to_dict(), sort_keys=True)
    left.solve(biased(epochs[20], 6, "G20", 90))
    assert json.dumps(a.to_dict(), sort_keys=True) == saved


@pytest.mark.parametrize(
    "settings",
    [
        {"fde_history_epochs": 0},
        {"fde_history_epochs": 1.5},
        {"fde_likelihood_ratio": float("nan")},
        {"fde_history_max_gap_s": 0},
    ],
)
def test_invalid_diagnosis_configuration_rejected(settings):
    with pytest.raises(ValueError):
        SolverConfig(**settings)


def test_parity_fault_variance_and_innovation_calibration(data):
    nav, epochs, _ = data
    engine = PositioningEngine(nav)
    frame = biased(epochs[0], 6, "G07", 0)
    fit = engine._fit(engine._prepare(frame), frame.gps_sow, np.zeros(4))
    projection = np.eye(6) - fit.h @ np.linalg.pinv(fit.h)
    j = 1
    q = projection[:, j]
    variance = 1 / projection[j, j]
    rng = np.random.default_rng(621001)
    noise = rng.normal(size=(12000, 2, 6))
    residual = noise @ projection + 30 * q
    bias = residual[:, :, j] / projection[j, j]
    remaining = residual[:, 1] - bias[:, 1, None] * q
    statistic = np.sum(remaining**2, axis=1) + np.diff(bias, axis=1)[:, 0] ** 2 / (2 * variance)
    assert np.var(bias[:, 0]) == pytest.approx(variance, rel=0.04)
    assert np.mean(statistic) == pytest.approx(2, rel=0.04)
    # Two residual degrees of freedom; check calibration, not a tuned threshold.
    assert 0.0002 < np.mean(statistic > 13.815510557964274) < 0.002


def test_new_forward_generator_round_trip_and_determinism():
    import importlib.util

    from gnss_workbench.settings import PROJECT_ROOT

    path = PROJECT_ROOT / "scripts/validate_six_satellite.py"
    spec = importlib.util.spec_from_file_location("six_satellite_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    for lat, lon, height, time_s, clock in [
        (35.0, 139.0, 60.0, 518100.25, -43000),
        (36.0, 138.0, 120.0, 518800.75, 71000),
    ]:
        xyz = module.ecef(lat, lon, height)
        observations = tuple(
            module.Observation(s, module.simulate_range(nav, s, xyz, clock, time_s)[0])
            for s in sorted(nav["ephemerides"])[:6]
        )
        frame = module.Epoch(7, 1316, time_s, observations)
        baseline, _ = PositioningEngine(nav).solve(frame)
        assert np.linalg.norm(np.array([baseline.x_m, baseline.y_m, baseline.z_m]) - xyz) < 0.001
        assert baseline.clock_bias_m == pytest.approx(clock, abs=0.001)
    # This is a development-only seed, never one of the frozen validation seeds.
    a = next(module.scenarios(nav, 621000, "continuous"))
    b = next(module.scenarios(nav, 621000, "continuous"))
    assert a == b
    assert a[1] == "clean" and len(a[2]) == 80
