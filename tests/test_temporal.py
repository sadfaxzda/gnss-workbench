"""Parity regression checked against independent stacked measurement-space LS."""

from dataclasses import replace

import numpy as np
import pytest

from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.core.temporal import TemporalParityMonitor, observability
from gnss_workbench.io import navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


def geometry(n, rng):
    los = rng.normal(size=(n, 3))
    los /= np.linalg.norm(los, axis=1)[:, None]
    return np.column_stack((los, np.ones(n)))


@pytest.mark.parametrize("n", [5, 6, 7, 8])
def test_temporal_projection_matches_full_measurement_space_least_squares(n):
    rng = np.random.default_rng(640001 + n)
    keys = tuple(f"G{i + 1:02}" for i in range(n))
    count, target = 10, 2
    monitor = TemporalParityMonitor(16, 5, 0.001)
    matrices, measurements = [], []
    for t in range(count):
        h = geometry(n, rng)
        # Deliberately unrelated receiver increments/clock at every epoch:
        # the monitor must impose NO receiver dynamics or fixed coordinates.
        y = h @ rng.normal(0, 300, 4) + rng.normal(0, 0.8, n)
        y[target] += 40 + 0.3 * t
        residual = y - h @ np.linalg.lstsq(h, y, rcond=None)[0]
        evidence = monitor.observe(t, keys, h, residual, 1)
        matrices.append(h)
        measurements.extend(y)
    assert evidence is not None and evidence.epochs == count and evidence.detected
    for candidate in range(n):
        order = 2
        design = np.zeros((n * count, 4 * count + order))
        for t, h in enumerate(matrices):
            design[t * n : (t + 1) * n, 4 * t : 4 * (t + 1)] = h
            design[t * n + candidate, -order:] = [1, t - count + 1][:order]
        parameters = np.linalg.lstsq(design, measurements, rcond=None)[0]
        residual = measurements - design @ parameters
        assert evidence.statistics[candidate] == pytest.approx(residual @ residual, abs=1e-7)
        assert evidence.bias[candidate] == pytest.approx(parameters[-order], abs=1e-7)
        assert evidence.drift[candidate] == pytest.approx(
            parameters[-1] if order == 2 else 0, abs=1e-7
        )


def test_weak_persistent_fault_detected_below_snapshot_gate_and_recovery_is_current():
    rng = np.random.default_rng(640010)
    h = geometry(6, rng)
    projection = np.eye(6) - h @ np.linalg.pinv(h)
    keys = tuple(f"G{i + 1:02}" for i in range(6))
    monitor = TemporalParityMonitor(16, 5, 0.001)
    # Instantaneous parity energy = 9, below chi2(2, .999)=13.8155.
    residual = projection[:, 0] * 3 / np.sqrt(projection[0, 0])
    detected = []
    for t in range(12):
        e = monitor.observe(t, keys, h, residual, 1)
        detected.append(e is not None and e.detected)
    assert any(detected[3:]) and not detected[0]
    recovered = monitor.observe(12, keys, h, np.zeros(6), 1)
    assert recovered is None or not recovered.detected
    # Changing visibility/gaps/non-increasing time must clear the model.
    assert monitor.observe(12, keys, h, residual, 1) is None
    assert monitor.observe(30, keys, h, residual, 1) is None
    assert monitor.observe(31, (*keys[:-1], "G25"), h, residual, 1) is None
    assert monitor.observe(32, keys[:4], h[:4], np.zeros(4), 1) is None
    assert not monitor.samples


def test_many_windows_do_not_reuse_a_single_epoch_false_alarm_budget():
    rng = np.random.default_rng(640011)
    h = geometry(6, rng)
    projection = np.eye(6) - h @ np.linalg.pinv(h)
    monitor = TemporalParityMonitor(16, 5, 0.001)
    keys = tuple(f"G{i + 1:02}" for i in range(6))
    alarms = 0
    for t in range(6000):
        result = monitor.observe(t, keys, h, projection @ rng.normal(size=6), 1)
        alarms += result is not None and result.detected
    assert alarms / 6000 < 0.003


def test_new_larger_noise_scale_downweights_all_stored_temporal_evidence():
    rng = np.random.default_rng(640012)
    h = geometry(6, rng)
    keys = tuple(f"G{i + 1:02}" for i in range(6))
    projection = np.eye(6) - h @ np.linalg.pinv(h)
    nominal, large = TemporalParityMonitor(16, 5, 0.001), TemporalParityMonitor(16, 5, 0.001)
    for t in range(10):
        r = projection @ (rng.normal(size=6) + np.array([15, 0, 0, 0, 0, 0]))
        nominal.observe(t, keys, h, r, 1)
        large.observe(t, keys, h, r, 3)
    a = nominal.observe(10, keys, h, r, 3)
    b = large.observe(10, keys, h, r, 3)
    assert a is not None and b is not None
    assert a.statistics == pytest.approx(b.statistics)


def test_four_five_star_boundaries_and_observability_are_honest():
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    epochs = list(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))
    for n in (4, 5):
        engine = PositioningEngine(nav)
        for epoch in epochs[:25]:
            observations = tuple(
                replace(o, pseudorange_m=o.pseudorange_m + (80 if j == 0 else 0))
                for j, o in enumerate(epoch.observations[:n])
            )
            baseline, solution = engine.solve(replace(epoch, observations=observations))
            assert solution.n_used == n and solution.excluded_sats == solution.flagged_sats == []
            assert solution.x_m == baseline.x_m
            if n == 4:
                assert solution.status == "NO_REDUNDANCY"
                assert "零残差不能证明无故障" in solution.reason
            else:
                assert solution.status == "SUSPECT" and "身份未确认" in solution.reason
            trace = next(
                t for t in solution.algorithm_trace if t.get("stage") == "fault_observability"
            )
            assert trace["redundancy"] == n - 4 and not trace["can_validate_exclusion"]
        # No previously observed signal can bypass 0/3 satellite observability.
        for n_bad in (0, 3):
            _, invalid = engine.solve(
                replace(epochs[25], observations=epochs[25].observations[:n_bad])
            )
            assert not invalid.has_position and not engine._temporal.samples


def test_observability_scale_and_unobservable_directions():
    rng = np.random.default_rng(640013)
    h = geometry(6, rng)
    keys = tuple(f"G{i + 1:02}" for i in range(6))
    one, two = (observability(h, sigma, 0.001, keys) for sigma in (1, 2))
    for a, b in zip(one["satellites"], two["satellites"], strict=True):
        assert b["detectable_bias_m"] == pytest.approx(2 * a["detectable_bias_m"])


def test_temporal_feature_is_ablatable_without_changing_ordinary_solution():
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    epoch = next(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))
    a, b = [
        PositioningEngine(nav, SolverConfig(temporal_parity=v)).solve(epoch) for v in (False, True)
    ]
    for key in ("x_m", "y_m", "z_m", "clock_bias_m", "pdop", "residual_rms_m"):
        assert getattr(a[0], key) == getattr(b[0], key)
    assert not any(t.get("stage") == "temporal_parity" for t in a[1].algorithm_trace)


def test_fault_switch_discards_inconsistent_old_amplitude_model():
    rng = np.random.default_rng(640014)
    h = geometry(7, rng)
    keys = tuple(f"G{i + 1:02}" for i in range(7))
    projection = np.eye(7) - h @ np.linalg.pinv(h)
    monitor = TemporalParityMonitor(16, 5, 0.001)
    for t in range(12):
        residual = projection[:, 0] * 80 + projection @ rng.normal(0, 0.4, 7)
        monitor.observe(t, keys, h, residual, 1)
    for t in range(12, 18):
        residual = projection[:, 1] * -90 + projection @ rng.normal(0, 0.4, 7)
        evidence = monitor.observe(t, keys, h, residual, 1)
        if t >= 14:
            assert evidence is not None and evidence.detected
            assert evidence.start_time >= 12
            assert int(np.argmin(evidence.statistics)) == 1
            assert not evidence.passing[0]


def test_observation_reordering_preserves_identity_and_history():
    rng = np.random.default_rng(640015)
    h = geometry(6, rng)
    keys = tuple(f"G{i + 1:02}" for i in range(6))
    projection = np.eye(6) - h @ np.linalg.pinv(h)
    normal, reordered = (TemporalParityMonitor(16, 5, 0.001) for _ in range(2))
    for t in range(8):
        residual = projection[:, 2] * 80 + projection @ rng.normal(0, 0.4, 6)
        permutation = rng.permutation(6)
        a = normal.observe(t, keys, h, residual, 1)
        b = reordered.observe(
            t, tuple(keys[j] for j in permutation), h[permutation], residual[permutation], 1
        )
        assert (a is None) == (b is None)
        if a is not None and b is not None:
            assert a.epochs == b.epochs and a.keys == b.keys
            assert a.statistics == pytest.approx(b.statistics)
