"""Independent change-of-identity and no-change evidence sequences."""

import numpy as np
import pytest

from gnss_workbench.core.diagnosis import AmbiguityResolver


def test_repeated_weak_current_evidence_can_overturn_a_stale_identity():
    keys = tuple(f"G{i + 1:02}" for i in range(6))
    old, new = (AmbiguityResolver(16, 5, 20) for _ in range(2))
    decisions = []
    for t in range(20):
        values = np.array([0, 4, 10, 10, 10, 10] if t < 16 else [4, 0, 10, 10, 10, 10])
        result = []
        for resolver, enabled in [(old, False), (new, True)]:
            result.append(
                resolver.observe(
                    t,
                    keys,
                    dict(zip(keys, values, strict=True)),
                    set(keys),
                    require_current_agreement=True,
                    use_unconfirmed_history=True,
                    detect_identity_change=enabled,
                )
            )
        decisions.append(result)
    a, b = decisions[-1]
    assert a.tentative == keys[0] and a.selected is None
    assert b.selected == keys[1] and b.reset_reason == "cumulative_identity_change"
    assert b.change_start_time == 16 and b.epochs == 4
    assert b.change_log_ratio is not None and b.change_log_ratio > np.log(20)


def test_single_weak_outlier_does_not_trigger_cumulative_change():
    keys = ("G01", "G02", "G03")
    resolver = AmbiguityResolver(16, 5, 20)
    for t in range(50):
        cost = [0, 4, 10] if t != 30 else [4, 0, 10]
        decision = resolver.observe(
            t,
            keys,
            dict(zip(keys, cost, strict=True)),
            set(keys),
            use_unconfirmed_history=True,
            detect_identity_change=True,
        )
        assert decision.reset_reason != "cumulative_identity_change"
        if t >= 4:
            assert decision.tentative == "G01"


def test_statistic_offsets_and_observation_order_do_not_change_a_split():
    keys = ("G01", "G02", "G03")
    a, b = (AmbiguityResolver(16, 5, 20) for _ in range(2))
    for t in range(24):
        cost = np.array([0, 4, 10] if t < 16 else [4, 0, 10], dtype=float)
        x = a.observe(t, keys, dict(zip(keys, cost, strict=True)), detect_identity_change=True)
        y = b.observe(
            t, keys[::-1], dict(zip(keys, cost + 37 * t, strict=True)), detect_identity_change=True
        )
        assert x.selected == y.selected and x.reset_reason == y.reset_reason
        assert x.change_start_time == y.change_start_time
        assert x.change_log_ratio == pytest.approx(y.change_log_ratio)


def test_parity_noise_without_fault_change_rarely_triggers_a_change():
    rng = np.random.default_rng(650101)
    h = np.column_stack((rng.normal(size=(7, 3)), np.ones(7)))
    s = np.eye(7) - h @ np.linalg.pinv(h)
    keys = tuple(f"G{i + 1:02}" for i in range(7))
    monitor = AmbiguityResolver(16, 5, 20)
    changes = 0
    for t in range(3000):
        residual = s @ (rng.normal(size=7) + np.array([30, 0, 0, 0, 0, 0, 0]))
        scores = residual @ residual - residual**2 / np.diag(s)
        decision = monitor.observe(
            t,
            keys,
            dict(zip(keys, scores, strict=True)),
            require_current_agreement=True,
            detect_identity_change=True,
        )
        changes += decision.reset_reason == "cumulative_identity_change"
    assert changes / 3000 < 0.01
