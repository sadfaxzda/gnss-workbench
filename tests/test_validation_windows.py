"""Evaluation counts every labelled boundary without selecting on solution error."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "validation_suite", Path(__file__).resolve().parents[1] / "scripts/validate_six_satellite.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(i, satellite, bias=30):
    return dict(
        epoch_id=100 + 7 * i,
        gps_sow=0.2 * i,
        fault_satellite=satellite,
        bias_m=bias if satellite else 0,
    )


def test_all_three_rapid_switches_are_included_and_recovery_is_separate():
    rows = [record(i, ["A", "B", "C", "A"][i // 15] if i < 60 else "") for i in range(80)]
    groups = module.event_windows(rows)
    assert len(groups["first10_after_onset"]) == 10
    assert len(groups["first10_after_switch"]) == 30
    assert [r["epoch_id"] for r in groups["first10_after_switch"]] == [
        rows[i]["epoch_id"] for start in (15, 30, 45) for i in range(start, start + 10)
    ]
    assert len(groups["first10_after_recovery"]) == 10


def test_short_faults_stop_at_next_transition_and_sign_reversal_counts():
    rows = [
        record(0, ""),
        record(1, "A"),
        record(2, "A", -30),
        record(3, ""),
        record(4, "B"),
        record(5, "C"),
    ]
    groups = module.event_windows(rows)
    selected = [r["epoch_id"] for values in groups.values() for r in values]
    assert len(selected) == len(set(selected)) == 5
    assert len(groups["first10_after_switch"]) == 2
    assert len(groups["first10_after_recovery"]) == 1
    assert len(groups["first10_after_onset"]) == 2


def test_normal_stream_has_no_fault_boundaries():
    assert all(
        not values for values in module.event_windows([record(i, "") for i in range(20)]).values()
    )


def target_row():
    return dict(
        required_h_p95_m=2.0,
        required_position_availability=1.0,
        required_success10=1.0,
        correct_flag_recall=None,
        clean_false_alarm_rate=0.0,
        clean_status_false_alarm_rate=0.0,
        state_correct_rate=1.0,
        clock_p95_m=1.0,
    )


def test_target_denominator_excludes_expected_no_position_epochs():
    row = target_row()
    row.update(h_p95_m=2, position_availability=0.5, success_within_10m=0.5)
    result = module.targets({"variable/new": row})["variable"]
    assert result["all_measured_targets_met"]
    row["state_correct_rate"] = 0.9
    assert not module.targets({"variable/new": row})["variable"]["all_measured_targets_met"]


def test_no_position_output_cannot_pass_by_hiding_the_error_quantile():
    row = target_row()
    row.update(required_h_p95_m=None, required_position_availability=0, required_success10=0)
    result = module.targets({"clean/new": row})["clean"]
    assert result["checks"]["h_p95"] is False
    assert result["checks"]["availability"] is False
