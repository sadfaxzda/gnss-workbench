"""Independent statistical and causal tests; no diagnosis labels in scale fitting."""

from dataclasses import replace

import numpy as np
import pytest
from scipy.stats import chi2

from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.noise import ParityNoiseEstimator
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.io import navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT


def geometry(n=6):
    rng = np.random.default_rng(630001)
    los = rng.normal(size=(n, 3))
    los /= np.linalg.norm(los, axis=1)[:, None]
    h = np.column_stack((los, np.ones(n)))
    return h, np.eye(n) - h @ np.linalg.pinv(h), tuple(f"G{i + 1:02}" for i in range(n))


@pytest.mark.parametrize("n", [5, 6, 7, 8])
def test_whitening_changing_geometry_has_correct_chi_square_distribution(n):
    h, old_projection, _ = geometry(n)
    rng = np.random.default_rng(630002)
    changed = h.copy()
    changed[:, :3] += rng.normal(0, 0.15, (n, 3))
    basis = np.linalg.svd(changed, full_matrices=True)[0][:, 4:]
    covariance = np.eye(n - 4) + basis.T @ old_projection @ basis
    old, new = rng.normal(size=(2, 20000, n))
    delta = (new - old @ old_projection) @ basis
    statistics = np.sum(delta * np.linalg.solve(covariance, delta.T).T, axis=1)
    assert np.mean(statistics) == pytest.approx(n - 4, rel=0.035)
    assert np.mean(statistics > chi2.ppf(0.99, n - 4)) == pytest.approx(0.01, abs=0.003)


@pytest.mark.parametrize("sigma", [0.8, 2.4])
def test_scale_and_false_alarm_calibration_with_persistent_bias_and_changes(sigma):
    h, projection, keys = geometry()
    rng = np.random.default_rng(630003)
    estimator = ParityNoiseEstimator(1, 5)
    clean_estimator = ParityNoiseEstimator(1, 5)
    scales, alarms = [], []
    for t in range(5000):
        error = rng.normal(0, sigma, 6)
        fault = np.zeros(6)
        fault[(t // 400) % 6] = 90 * (-1) ** (t // 400)
        evidence = estimator.observe(t, keys, h, projection @ (error + fault))
        clean = clean_estimator.observe(t, keys, h, projection @ error)
        if t > 100:
            scales.append(evidence.sigma_m)
            alarms.append(
                np.linalg.norm(projection @ error) ** 2 / evidence.sigma_m**2 > chi2.ppf(0.999, 2)
            )
            # Every transition here lies between independent pairs: constant
            # faults cancel and cannot inflate the noise estimate.
            assert evidence.sigma_m == pytest.approx(clean.sigma_m, abs=1e-10)
    assert np.median(scales) == pytest.approx(max(sigma, 1), rel=0.12)
    assert np.mean(alarms) < 0.015
    assert len(estimator.values) == 32


def test_a_fault_step_cannot_set_the_scale_or_affect_its_own_threshold():
    h, projection, keys = geometry()
    rng = np.random.default_rng(630004)
    left, right = ParityNoiseEstimator(1, 5), ParityNoiseEstimator(1, 5)
    for t in range(80):
        residual = projection @ rng.normal(0, 0.8, 6)
        a = left.observe(t, keys, h, residual)
        fault = np.zeros(6)
        fault[0] = 1000 if t >= 31 else 0
        b = right.observe(t, keys, h, residual + projection @ fault)
        if t <= 31:
            assert a == b  # Uses only completed past pairs, including at the step.
        assert b.sigma_m <= 1.2


def test_noise_history_resets_on_time_or_membership_but_not_input_order():
    h, projection, keys = geometry()
    rng = np.random.default_rng(630005)
    estimator = ParityNoiseEstimator(1, 5)
    for t in range(20):
        residual = projection @ rng.normal(0, 3, 6)
        estimator.observe(t, keys[::-1], h[::-1], residual[::-1])
    assert estimator.observe(20, keys, h, np.zeros(6)).pairs == 10
    assert estimator.observe(20, keys, h, np.zeros(6)).pairs == 0
    estimator.observe(21, keys, h, np.zeros(6))
    assert estimator.observe(50, keys, h, np.zeros(6)).pairs == 0
    estimator.observe(51, keys, h, np.zeros(6))
    assert estimator.observe(52, (*keys[:-1], "G20"), h, np.zeros(6)).pairs == 0
    assert estimator.observe(53, keys[:4], h[:4], np.zeros(4)).pairs == 0
    assert not estimator.values and estimator.pending is None


def test_engine_high_noise_preserves_baseline_and_reduces_false_exclusions():
    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    engines = [
        PositioningEngine(nav, SolverConfig(adaptive_noise=enabled)) for enabled in (False, True)
    ]
    rng = np.random.default_rng(630006)
    false = [0, 0]
    for original in read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"):
        epoch = replace(
            original,
            observations=tuple(
                replace(o, pseudorange_m=o.pseudorange_m + rng.normal(0, 2.3))
                for o in original.observations[:6]
            ),
        )
        outputs = [engine.solve(epoch) for engine in engines]
        for key in ("x_m", "y_m", "z_m", "clock_bias_m", "pdop", "residual_rms_m"):
            assert getattr(outputs[0][0], key) == pytest.approx(
                getattr(outputs[1][0], key), abs=1e-5
            )
        for i, (_, solution) in enumerate(outputs):
            false[i] += bool(solution.flagged_sats)
        trace = outputs[1][1].algorithm_trace[-1]
        assert trace["stage"] == "causal_noise_scale"
    assert false[1] / 600 < 0.05
    assert false[1] < false[0] / 5
    # Invalid input also clears scale evidence; it cannot survive a broken stream.
    engines[1].solve(replace(epoch, observations=(), data_error="broken observation"))
    assert not engines[1]._noise.values and engines[1]._noise.pending is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_iterations": 0},
        {"max_iterations": 2.5},
        {"max_iterations": True},
        {"convergence_m": float("nan")},
        {"convergence_m": 0},
        {"elevation_mask_deg": float("nan")},
        {"elevation_mask_deg": 90},
        {"pdop_warning": float("inf")},
        {"pdop_warning": 0},
        {"max_faults": 1.5},
        {"max_hypotheses": True},
    ],
)
def test_invalid_configuration_cannot_silently_bypass_numerical_gates(kwargs):
    with pytest.raises(ValueError):
        SolverConfig(**kwargs)
