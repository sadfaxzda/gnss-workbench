"""Scale corrections and strictly past-only bias prediction, without receiver priors."""

import math

import pytest

from gnss_workbench.core.diagnosis import AmbiguityResolver


def test_larger_causal_scale_revokes_overconfident_old_identity():
    old, new = (AmbiguityResolver(16, 5, 20) for _ in range(2))
    for t in range(8):
        old.observe(t, ("A", "B"), {"A": 0, "B": 1})
        new.observe(t, ("A", "B"), {"A": 0, "B": 1}, noise_sigma_m=1)
    assert old.observe(8, ("A", "B"), {"A": 0, "B": 0}).selected == "A"
    decision = new.observe(8, ("A", "B"), {"A": 0, "B": 0}, noise_sigma_m=3)
    assert decision.selected is None
    assert decision.log_ratio == pytest.approx(4 / 9)
    assert decision.history_sigma_m == 3
    # A later small estimate cannot resurrect previously discounted evidence.
    later = new.observe(9, ("A", "B"), {"A": 0, "B": 0}, noise_sigma_m=1)
    assert later.log_ratio == pytest.approx(decision.log_ratio)
    assert later.selected is None


def test_scale_changes_are_equivalent_to_preweighted_evidence():
    changing, reference = (AmbiguityResolver(16, 5, 20) for _ in range(2))
    for t, scale in enumerate([1, 2, 1, 3]):
        changing.observe(t, ("A", "B"), {"A": 0, "B": 0.8 / scale**2}, noise_sigma_m=scale)
        reference.observe(t, ("A", "B"), {"A": 0, "B": 0.8 / 9})
    a = changing.observe(4, ("A", "B"), {"A": 0, "B": 0}, noise_sigma_m=3)
    b = reference.observe(4, ("A", "B"), {"A": 0, "B": 0})
    assert a.log_ratio == pytest.approx(b.log_ratio)
    assert a.window_shares == pytest.approx(b.window_shares)


def test_scale_increase_updates_old_amplitude_uncertainty_too():
    resolver = AmbiguityResolver(16, 5, 20)
    keys, scores = ("A", "B"), {"A": 0.1, "B": 1}
    resolver.observe(0, keys, scores, set(keys), {"A": (30, 1), "B": (0, 1)}, 13.8, noise_sigma_m=1)
    result = resolver.observe(
        1, keys, scores, set(keys), {"A": (42, 9), "B": (0, 9)}, 13.8, noise_sigma_m=3
    )
    assert result.innovation_statistic == pytest.approx(0.1 + 144 / 18)
    assert result.epochs == 2


@pytest.mark.parametrize("scale", [0, -1, math.nan, math.inf])
def test_invalid_scale_is_rejected(scale):
    with pytest.raises(ValueError, match="Noise scale"):
        AmbiguityResolver(16, 5, 20).observe(0, ("A", "B"), {"A": 0, "B": 1}, noise_sigma_m=scale)
