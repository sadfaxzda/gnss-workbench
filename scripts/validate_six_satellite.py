"""New forward-simulated six-satellite cases; never reuses D02 observations.

Freeze the method before running held-out seeds. Preserve every epoch and report
confirmed and tentative identities separately. Successful execution is not a
claim that all numerical targets are met. Truth is used only after solving.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from itertools import combinations
from pathlib import Path

import numpy as np

from gnss_workbench.core.atmosphere import ionosphere, troposphere
from gnss_workbench.core.coordinates import (
    E2,
    A,
    azimuth_elevation,
    enu_rotation,
    geodetic,
    local_enu,
)
from gnss_workbench.core.ephemeris import C, rotate_to_receive, satellite_state, transmit_state
from gnss_workbench.core.models import Epoch, Observation, SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.evaluation import evaluate_run
from gnss_workbench.io import export_solutions, navigation_from
from gnss_workbench.settings import COURSE_ROOT, PROJECT_ROOT


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def ecef(latitude, longitude, height):
    lat, lon = map(math.radians, (latitude, longitude))
    n = A / math.sqrt(1 - E2 * math.sin(lat) ** 2)
    return np.array(
        [
            (n + height) * math.cos(lat) * math.cos(lon),
            (n + height) * math.cos(lat) * math.sin(lon),
            (n * (1 - E2) + height) * math.sin(lat),
        ]
    )


def simulate_range(nav, sat, xyz, clock_m, sow):
    """Invert the course observation equation by a forward fixed-point solve.

    Independent of PositioningEngine/_linearize; shared broadcast and atmosphere
    primitives have course checkpoint regression. This is not field validation.
    """
    eph = nav["ephemerides"][sat]
    p = float(np.linalg.norm(satellite_state(eph, sow)[0] - xyz)) + clock_m
    lat, lon, height = geodetic(xyz)
    for _ in range(12):
        satellite, code_clock = transmit_state(eph, sow, p)
        satellite = rotate_to_receive(satellite, (p + C * code_clock - clock_m) / C)
        az, el = azimuth_elevation(xyz, satellite)
        correction = ionosphere(lat, lon, az, el, sow - clock_m / C, nav["alpha"], nav["beta"])
        correction += troposphere(lat, height, el)
        new_p = float(np.linalg.norm(satellite - xyz)) + clock_m - C * code_clock + correction
        if abs(new_p - p) < 1e-6:
            return new_p, el
        p = new_p
    raise RuntimeError("Forward pseudorange synthesis did not converge")


def scenarios(nav, seed, suite, n_satellites=6):
    rng = np.random.default_rng(seed)
    satellites = sorted(nav["ephemerides"])
    for group_index, group in enumerate(combinations(satellites, n_satellites)):
        kinds = (
            [("isolated", target, sign) for target in group for sign in (-1, 1)]
            if suite == "cold"
            else [
                (kind, str(rng.choice(group)), int(rng.choice([-1, 1])))
                for kind in ("clean", "common", "cold_stream", "step", "ramp", "switch", "rapid")
            ]
        )
        if suite == "eight":
            # Predetermined exhaustive satellite/sign coverage, before any solve.
            # Each case gets its own trajectory, clock and noise from the seed.
            kinds = [("clean", group[0], 1), ("common", group[0], -1), ("common", group[0], 1)]
            kinds += [
                (kind, target, sign)
                for kind in ("cold_stream", "step", "ramp", "switch", "rapid")
                for target in group
                for sign in (-1, 1)
            ]
        for case_index, (kind, target, sign) in enumerate(kinds):
            length = 1 if kind == "isolated" else 80
            # Rejection is solely for the stated >3-degree observation domain,
            # before injecting faults or solving. Geometry/precision never select cases.
            for _attempt in range(100):
                origin = ecef(
                    rng.uniform(33.5, 37.5), rng.uniform(136.5, 141.5), rng.uniform(30, 180)
                )
                start = float(rng.uniform(517900, 519800))
                if all(
                    azimuth_elevation(origin, satellite_state(nav["ephemerides"][s], t)[0])[1]
                    > math.radians(4)
                    for s in group
                    for t in (start, start + length)
                ):
                    break
            else:
                raise RuntimeError("Cannot sample course-compatible visibility")
            rotation = enu_rotation(origin)
            velocity = rng.uniform(-4, 4, 2)
            radius = rng.uniform(5, 25)
            frequency = rng.uniform(0.025, 0.065)
            phase = rng.uniform(0, 2 * math.pi, n_satellites)
            clock0, clock_rate = rng.uniform(-8e4, 8e4), rng.uniform(-4, 4)
            amplitude = 30.0 if case_index % 2 == 0 else float(rng.uniform(30, 120))
            if kind == "ramp":
                amplitude = float(rng.uniform(60, 120))
            others = [s for s in group if s != target]
            second, third = rng.choice(others, 2, replace=False)
            sigma = 2.4 if suite == "stress" else 0.8
            frames, labels = [], []
            for t in range(length):
                enu = np.array(
                    [
                        velocity[0] * t + radius * math.sin(frequency * t),
                        velocity[1] * t + radius * (math.cos(frequency * t) - 1),
                        2 * math.sin(0.017 * t),
                    ]
                )
                xyz = origin + rotation.T @ enu
                clock = clock0 + clock_rate * t + 4 * math.sin(0.031 * t)
                active = (
                    kind == "isolated"
                    or (kind == "cold_stream" and t < 60)
                    or (kind in {"step", "ramp"} and 10 <= t < 70)
                    or (kind == "switch" and t < 70)
                    or (kind == "rapid" and t < 60)
                )
                fault_sat = target if active else ""
                bias = sign * amplitude if active else 0.0
                if kind == "switch" and 35 <= t < 70:
                    fault_sat, bias = str(second), -sign * amplitude
                if kind == "rapid" and active:
                    fault_sat = str([target, second, third, target][t // 15])
                    bias *= (-1) ** (t // 15)
                if kind == "ramp" and active:
                    bias *= (t - 9) / 60
                common = sign * 100.0 if kind == "common" and 10 <= t < 60 else 0.0
                observations = []
                for j, sat in enumerate(group):
                    p, el = simulate_range(nav, sat, xyz, clock, start + t)
                    assert math.degrees(el) > 3, "Generated observation below course mask"
                    noise = float(rng.normal(0, sigma) + 0.25 * math.sin(0.07 * t + phase[j]))
                    observations.append(
                        Observation(
                            sat, p + noise + common + (bias if sat == fault_sat else 0), None
                        )
                    )
                frames.append(Epoch(t, 1316, start + t, tuple(observations)))
                labels.append(
                    dict(
                        epoch_id=t,
                        gps_week=1316,
                        gps_sow=start + t,
                        x_m=float(xyz[0]),
                        y_m=float(xyz[1]),
                        z_m=float(xyz[2]),
                        clock_bias_m=clock + common,
                        expected_state="POSITION_REQUIRED",
                        fault_sat=fault_sat,
                        fault_bias_m=bias,
                        common_bias_m=common,
                        event=kind,
                    )
                )
            name = f"set{group_index:02}-{case_index:02}-{kind}"
            yield (
                name,
                kind,
                frames,
                labels,
                dict(visibility_draws=_attempt + 1, noise_sigma_m=sigma),
            )


def summarize(rows):
    faults = [r for r in rows if abs(r["bias_m"]) >= 30 and r["fault_satellite"]]
    clean = [r for r in rows if not r["fault_satellite"]]
    errors = [r["horizontal_error_m"] for r in rows if r["horizontal_error_m"] is not None]
    fault_errors = [r["horizontal_error_m"] for r in faults if r["horizontal_error_m"] is not None]
    clock_errors = [r["clock_error_m"] for r in rows if r["clock_error_m"] is not None]
    required = [
        r
        for r in rows
        if r.get("expected_state", "POSITION_REQUIRED") in {"POSITION_REQUIRED", "NO_REDUNDANCY"}
    ]
    state_rows = [r for r in rows if r.get("state_correct") is not None]
    return dict(
        epochs=len(rows),
        position_availability=len(errors) / len(rows),
        h_p95_m=float(np.percentile(errors, 95)) if errors else None,
        success_within_10m=sum(e <= 10 for e in errors) / len(rows),
        strong_fault_epochs=len(faults),
        correct_flag_recall=sum(r["correct_flag"] for r in faults) / len(faults)
        if faults
        else None,
        confirmed_correct_recall=sum(r["confirmed_correct"] for r in faults) / len(faults)
        if faults
        else None,
        fault_only_h_p95_m=float(np.percentile(fault_errors, 95)) if fault_errors else None,
        fault_only_success10=sum(e <= 10 for e in fault_errors) / len(faults) if faults else None,
        wrong_exclusions=sum(r["wrong_exclusion"] for r in rows),
        confirmed_wrong_exclusions=sum(r["confirmed_wrong"] for r in rows),
        clean_false_alarm_rate=sum(bool(r["flagged"]) for r in clean) / len(clean)
        if clean
        else None,
        clock_p95_m=float(np.percentile(clock_errors, 95)) if clock_errors else None,
        provisional_epochs=sum(r["provisional"] for r in rows),
        history_change_resets=sum(r["change_reset"] for r in rows),
        statuses=dict(Counter(r["status"] for r in rows)),
        strong_fault_status_alert_rate=sum(
            r["status"] in {"SUSPECT", "FAULT_EXCLUDED", "FAULT_MITIGATED"} for r in faults
        )
        / len(faults)
        if faults
        else None,
        clean_status_false_alarm_rate=sum(
            r["status"] in {"SUSPECT", "FAULT_EXCLUDED", "FAULT_MITIGATED"} for r in clean
        )
        / len(clean)
        if clean
        else None,
        required_position_availability=sum(r["horizontal_error_m"] is not None for r in required)
        / len(required)
        if required
        else None,
        required_success10=sum(
            r["horizontal_error_m"] is not None and r["horizontal_error_m"] <= 10 for r in required
        )
        / len(required)
        if required
        else None,
        required_h_p95_m=float(
            np.percentile(
                [r["horizontal_error_m"] for r in required if r["horizontal_error_m"] is not None],
                95,
            )
        )
        if any(r["horizontal_error_m"] is not None for r in required)
        else None,
        state_check_epochs=len(state_rows),
        state_correct_rate=sum(r["state_correct"] for r in state_rows) / len(state_rows)
        if state_rows
        else None,
    )


def targets(metrics):
    result = {}
    for kind, row in metrics.items():
        if not kind.endswith("/new"):
            continue
        scenario = kind.split("/")[0]
        normal = scenario in {"clean", "common"}
        checks = dict(
            h_p95=row["required_h_p95_m"] <= (5 if normal else 10)
            if row["required_h_p95_m"] is not None
            else (False if row["required_position_availability"] is not None else None),
            availability=row["required_position_availability"] >= 0.99
            if row["required_position_availability"] is not None
            else None,
            success10=row["required_success10"] >= 0.95
            if row["required_success10"] is not None
            else None,
            fault_recall=row["correct_flag_recall"] >= 0.9
            if row["correct_flag_recall"] is not None
            else None,
            clean_false_alarm=row["clean_false_alarm_rate"] <= 0.05
            if row["clean_false_alarm_rate"] is not None
            else None,
            clean_status_false_alarm=row["clean_status_false_alarm_rate"] <= 0.05
            if row["clean_status_false_alarm_rate"] is not None
            else None,
            special_states=row["state_correct_rate"] == 1
            if row["state_correct_rate"] is not None
            else None,
            common_clock=row["clock_p95_m"] <= 10 if scenario == "common" else None,
        )
        result[scenario] = dict(
            checks=checks, all_measured_targets_met=False not in checks.values()
        )
    return result


def event_windows(rows, count=10):
    """All labelled transitions, evaluated only AFTER solving, in received order.

    Each window stops at the next transition. Never duplicate an epoch when
    faults last fewer than `count` samples, or assume contiguous epoch IDs/1 Hz.
    A sign reversal on the same satellite is also a changed fault condition.
    """
    groups = {f"first{count}_after_{kind}": [] for kind in ("onset", "switch", "recovery")}

    def identity(row):
        return (
            (row["fault_satellite"], math.copysign(1, row["bias_m"]))
            if row["fault_satellite"] and row["bias_m"]
            else None
        )

    previous = None
    active, remaining = None, 0
    for row in rows:
        current = identity(row)
        if current != previous:
            kind = "recovery" if current is None else "onset" if previous is None else "switch"
            active, remaining = f"first{count}_after_{kind}", count
        if active is not None and remaining > 0:
            groups[active].append(row)
            remaining -= 1
        previous = current
    return groups


def irregular_scenarios(nav, seed):
    """Variable sample times, accelerating motion and unannounced fault changes.

    These profiles differ structurally from the development generator. No fixed
    15-epoch switching schedule or locally exactly linear bias is assumed here.
    """
    rng = np.random.default_rng(seed)
    satellites = sorted(nav["ephemerides"])
    for group_index, group in enumerate(combinations(satellites, 6)):
        for kind in ["random_switch", "nonlinear_bias", "intermittent"]:
            gaps = rng.uniform(0.2, 2.0, 95)
            elapsed = np.r_[0.0, np.cumsum(gaps)]
            for _attempt in range(100):
                origin = ecef(
                    rng.uniform(33.5, 37.5), rng.uniform(136.5, 141.5), rng.uniform(30, 180)
                )
                start = float(rng.uniform(517900, 519700))
                if all(
                    azimuth_elevation(origin, satellite_state(nav["ephemerides"][sat], time)[0])[1]
                    > math.radians(4)
                    for sat in group
                    for time in [start, start + elapsed[-1]]
                ):
                    break
            else:
                raise RuntimeError("Could not generate admissible visibility")
            rotation = enu_rotation(origin)
            enu, velocity = np.zeros(3), rng.uniform(-3, 3, 3)
            velocity[2] *= 0.1
            clock = float(rng.uniform(-8e4, 8e4))
            phases = rng.uniform(0, 2 * math.pi, 6)
            remaining, target, bias = 0, "", 0.0
            fixed_target = str(rng.choice(group))
            sign, walk = int(rng.choice([-1, 1])), 0.0
            frames, labels = [], []
            for i, tau in enumerate(elapsed):
                dt = float(gaps[i - 1]) if i else 0.0
                acceleration = rng.normal(0, 0.15, 3)
                acceleration[2] *= 0.1
                enu += velocity * dt + 0.5 * acceleration * dt**2
                velocity += acceleration * dt
                xyz = origin + rotation.T @ enu
                clock += float(rng.normal(0, 2.0) * math.sqrt(dt))
                if kind == "nonlinear_bias":
                    walk += float(rng.normal(0, 2.0) * math.sqrt(dt))
                    target = fixed_target if i < 80 else ""
                    bias = (
                        sign * (30 + 0.25 * tau + 12 * math.sin(0.08 * tau) + walk)
                        if target
                        else 0.0
                    )
                else:
                    if remaining <= 0:
                        remaining = int(rng.integers(4, 24))
                        clean = rng.random() < (0.2 if kind == "random_switch" else 0.5)
                        target = "" if clean else str(rng.choice([s for s in group if s != target]))
                        bias = float(rng.choice([-1, 1]) * rng.uniform(20, 120)) if target else 0.0
                    remaining -= 1
                observations = []
                for j, sat in enumerate(group):
                    p, el = simulate_range(nav, sat, xyz, clock, start + tau)
                    assert math.degrees(el) > 3
                    noise = float(rng.normal(0, 0.8) + 0.25 * math.sin(0.07 * tau + phases[j]))
                    observations.append(
                        Observation(sat, p + noise + (bias if sat == target else 0.0))
                    )
                frames.append(Epoch(i, 1316, float(start + tau), tuple(observations)))
                labels.append(
                    dict(
                        epoch_id=i,
                        gps_week=1316,
                        gps_sow=float(start + tau),
                        x_m=float(xyz[0]),
                        y_m=float(xyz[1]),
                        z_m=float(xyz[2]),
                        clock_bias_m=clock,
                        expected_state="POSITION_REQUIRED",
                        fault_sat=target,
                        fault_bias_m=bias,
                        common_bias_m=0.0,
                        event=kind,
                    )
                )
            yield (
                f"set{group_index:02}-{kind}",
                kind,
                frames,
                labels,
                dict(
                    visibility_draws=_attempt + 1,
                    noise_sigma_m=0.8,
                    sampling="independent gaps 0.2..2.0 seconds",
                    profile=kind,
                ),
            )


def validation_scenarios(nav, seed, suite):
    if suite == "eight":
        yield from scenarios(nav, seed, suite, 8)
    elif suite == "irregular":
        yield from irregular_scenarios(nav, seed)
    elif suite in {"four", "five", "variable"}:
        count = {"four": 4, "five": 5, "variable": 8}[suite]
        for name, kind, frames, labels, generation in scenarios(nav, seed, "continuous", count):
            revised_frames, revised_labels = [], []
            for epoch, label in zip(frames, labels, strict=True):
                if suite == "variable":
                    # Drop input epochs to create real GPST gaps; never relabel
                    # timestamps without recomputing satellite positions/ranges.
                    if 20 <= epoch.epoch_id < 25 or 60 <= epoch.epoch_id < 66:
                        continue
                    n = (
                        [8] * 10
                        + [6] * 10
                        + [5] * 10
                        + [4] * 10
                        + [3] * 5
                        + [0] * 5
                        + [5] * 10
                        + [6] * 10
                        + [8] * 10
                    )[epoch.epoch_id]
                    epoch = replace(epoch, observations=epoch.observations[:n])
                revised = label.copy()
                if revised["fault_sat"] not in {o.sat_id for o in epoch.observations}:
                    revised.update(fault_sat="", fault_bias_m=0.0)
                revised["expected_state"] = geometry_expectation(nav, epoch, revised)
                revised_frames.append(epoch)
                revised_labels.append(revised)
            yield name, kind, revised_frames, revised_labels, generation
    elif suite == "seven":
        yield from scenarios(nav, seed, "continuous", 7)
    elif suite == "membership":
        # Generate all eight measurements independently, then change the visible
        # six every twelve epochs. Include faults leaving/re-entering visibility.
        # Truth changes only when the injected fault is no longer observed.
        for name, kind, frames, labels, generation in scenarios(nav, seed, "continuous", 8):
            changed, truth = [], []
            for epoch, label in zip(frames, labels, strict=True):
                offset = (epoch.epoch_id // 12) % 8
                observations = tuple(
                    o
                    for i, o in enumerate(epoch.observations)
                    if i not in {offset, (offset + 3) % 8}
                )
                changed.append(replace(epoch, observations=observations))
                revised = label.copy()
                if revised["fault_sat"] not in {o.sat_id for o in observations}:
                    revised.update(fault_sat="", fault_bias_m=0.0)
                truth.append(revised)
            yield name, kind, changed, truth, generation
    else:
        yield from scenarios(nav, seed, suite)


def geometry_expectation(nav, epoch, label):
    n = len(epoch.observations)
    if n < 4:
        return "NO_OBSERVATIONS" if n == 0 else "INVALID_INSUFFICIENT"
    # Predefined truth geometry, never selected by solver accuracy or status.
    xyz = np.array([label[k] for k in ["x_m", "y_m", "z_m"]])
    h = []
    for obs in epoch.observations:
        satellite, clock = transmit_state(
            nav["ephemerides"][obs.sat_id], epoch.gps_sow, obs.pseudorange_m
        )
        satellite = rotate_to_receive(
            satellite, (obs.pseudorange_m + C * clock - label["clock_bias_m"]) / C
        )
        delta = xyz - satellite
        h.append([*(delta / np.linalg.norm(delta)), 1])
    singular = np.linalg.svd(np.array(h), compute_uv=False)
    q = np.linalg.pinv(np.array(h))
    pdop = float(np.linalg.norm(q[:3]))
    if singular[-1] < 1e-8 or pdop > 30:
        return "GEOMETRY_WARNING"
    return "NO_REDUNDANCY" if n == 4 else "POSITION_REQUIRED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        choices=[
            "continuous",
            "cold",
            "stress",
            "seven",
            "membership",
            "four",
            "five",
            "variable",
            "irregular",
            "eight",
        ],
        required=True,
    )
    parser.add_argument(
        "--comparison",
        choices=[
            "iteration2",
            "iteration3",
            "iteration4",
            "iteration5",
            "iteration6",
            "iteration8",
            "ablation",
        ],
        default="iteration2",
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Choose an empty output directory; previous evidence is never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    nav_path = COURSE_ROOT / "data/navigation.json"
    nav = navigation_from(nav_path)
    (out / "navigation.json").write_bytes(nav_path.read_bytes())
    previous = SolverConfig(
        adaptive_noise=False,
        strict_fde_confirmation=False,
        use_unconfirmed_history=False,
        temporal_parity=False,
        algebraic_recovery=False,
        sequential_change_detection=False,
        complete_geometry_diagnosis=False,
    )
    configurations = (
        dict(
            previous=previous,
            new=SolverConfig(
                temporal_parity=False,
                algebraic_recovery=False,
                sequential_change_detection=False,
                complete_geometry_diagnosis=False,
            ),
        )
        if args.comparison == "iteration3"
        else dict(
            previous=replace(previous, provisional_fde=False, fde_change_detection=False),
            provisional_only=replace(previous, fde_change_detection=False),
            innovation_only=replace(previous, provisional_fde=False),
            new=previous,
        )
    )
    if args.comparison == "iteration4":
        configurations = dict(
            previous=SolverConfig(
                temporal_parity=False,
                algebraic_recovery=False,
                sequential_change_detection=False,
                complete_geometry_diagnosis=False,
            ),
            new=SolverConfig(sequential_change_detection=False, complete_geometry_diagnosis=False),
        )
    if args.comparison == "iteration5":
        configurations = dict(
            previous=SolverConfig(
                sequential_change_detection=False, complete_geometry_diagnosis=False
            ),
            new=SolverConfig(),
        )
    if args.comparison == "ablation":
        configurations = dict(previous=SolverConfig(enable_fde=False), new=SolverConfig())
    elif args.comparison == "iteration8":
        configurations = dict(
            previous=SolverConfig(coherent_proposals=False),
            new=SolverConfig(coherent_proposals=True),
        )
    elif args.comparison == "iteration6":
        configurations = dict(
            previous=SolverConfig(rescale_history=False),
            new=SolverConfig(),
        )
    else:
        # Preserve the meaning of historical comparison commands after new
        # defaults are introduced.
        configurations = {
            name: replace(config, rescale_history=False) for name, config in configurations.items()
        }
    if args.comparison not in {"iteration8", "ablation"}:
        configurations = {
            name: replace(config, coherent_proposals=False)
            for name, config in configurations.items()
        }
    code = [*Path("src/gnss_workbench/core").glob("*.py"), Path(__file__)]
    manifest = dict(
        suite=args.suite,
        comparison=args.comparison,
        seed=args.seed,
        configurations={n: asdict(c) for n, c in configurations.items()},
        scope="Forward-simulated new positions, trajectories, clock, noise and fault sequences. Shares supplied navigation and physical primitives; no D02 observations and no field/hidden-test claim.",
        navigation_sha256=hashlib.sha256(nav_path.read_bytes()).hexdigest(),
        code_sha256={
            str(p.resolve().relative_to(PROJECT_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in code
        },
        inputs={},
    )
    grouped = defaultdict(list)
    case_metrics = {}
    baseline_difference, violations, count = 0.0, 0, 0
    for name, kind, frames, labels, generation in validation_scenarios(nav, args.seed, args.suite):
        folder = out / name
        folder.mkdir()
        source, truth = folder / "input.jsonl", folder / "truth.csv"
        source.write_text(
            json.dumps(dict(type="meta", schema="GNSS-COURSE-1.0"))
            + "\n"
            + "".join(json.dumps(dict(type="epoch", **asdict(e))) + "\n" for e in frames),
            encoding="utf-8",
        )
        with truth.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(labels[0]))
            writer.writeheader()
            writer.writerows(labels)
        manifest["inputs"][name] = dict(
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(), **generation
        )
        reference_baselines = []
        for method, config in configurations.items():
            destination = folder / method
            destination.mkdir()
            engine = PositioningEngine(nav, config)
            baseline, solutions, rows = [], [], []
            with (destination / "diagnostics.jsonl").open("w", encoding="utf-8") as logs:
                for epoch, label in zip(frames, labels, strict=True):
                    b, s = engine.solve(epoch)
                    baseline.append(b)
                    solutions.append(s)
                    logs.write(json.dumps(s.to_dict(), ensure_ascii=False, allow_nan=False) + "\n")
                    xyz = np.array([label[k] for k in ["x_m", "y_m", "z_m"]])
                    error = (
                        float(np.linalg.norm(local_enu(np.array([s.x_m, s.y_m, s.z_m]), xyz)[:2]))
                        if s.has_position
                        else None
                    )
                    correct = bool(label["fault_sat"] and label["fault_sat"] in s.flagged_sats)
                    wrong = bool(set(s.excluded_sats) - {label["fault_sat"]})
                    rows.append(
                        dict(
                            case=name,
                            epoch_id=epoch.epoch_id,
                            gps_sow=epoch.gps_sow,
                            fault_satellite=label["fault_sat"],
                            bias_m=label["fault_bias_m"],
                            observations=len(epoch.observations),
                            expected_state=label["expected_state"],
                            state_correct=(
                                s.status in {"GEOMETRY_WARNING", "INVALID_GEOMETRY"}
                                if label["expected_state"] == "GEOMETRY_WARNING"
                                else s.status == label["expected_state"]
                            )
                            if label["expected_state"] != "POSITION_REQUIRED"
                            else None,
                            horizontal_error_m=error,
                            clock_error_m=abs(s.clock_bias_m - label["clock_bias_m"])
                            if s.clock_bias_m is not None
                            else None,
                            correct_flag=correct,
                            confirmed_correct=correct and s.status == "FAULT_EXCLUDED",
                            wrong_exclusion=wrong,
                            confirmed_wrong=wrong and s.status == "FAULT_EXCLUDED",
                            provisional=any(
                                c.get("selection_method") == "provisional_likelihood"
                                for c in s.candidate_scores
                            ),
                            change_reset=any(
                                c.get("history_reset_reason") == "fault_amplitude_change"
                                for c in s.candidate_scores
                            ),
                            status=s.status,
                            flagged=s.flagged_sats,
                            excluded=s.excluded_sats,
                            diagnostic_sigma_m=next(
                                (
                                    t["sigma_m"]
                                    for t in s.algorithm_trace
                                    if t.get("stage") == "causal_noise_scale"
                                ),
                                config.noise_sigma_m,
                            ),
                        )
                    )
            export_solutions(destination / "baseline.csv", baseline)
            export_solutions(destination / "improved.csv", solutions)
            write_json(destination / "evaluation.json", rows)
            evaluated = evaluate_run(source, truth, destination)
            violations += sum(v["contract_violation_count"] for v in evaluated.values())
            write_json(destination / "course_metrics.json", evaluated)
            if method == "previous":
                reference_baselines = baseline
            else:
                for left, right in zip(reference_baselines, baseline, strict=True):
                    assert left.status == right.status and left.n_used == right.n_used
                    for key in ["x_m", "y_m", "z_m", "clock_bias_m", "pdop", "residual_rms_m"]:
                        a, b = getattr(left, key), getattr(right, key)
                        assert (a is None) == (b is None)
                        if a is not None:
                            baseline_difference = max(baseline_difference, abs(a - b))
            grouped[f"{kind}/{method}"].extend(rows)
            grouped[f"all/{method}"].extend(rows)
            case_metrics[f"{name}/{method}"] = summarize(rows)
            for n in sorted({r["observations"] for r in rows}):
                grouped[f"observations_{n}/{method}"].extend(
                    r for r in rows if r["observations"] == n
                )
            for window, affected in event_windows(rows).items():
                if affected:
                    grouped[f"{window}/{method}"].extend(affected)
        count += 1
        if count % 14 == 0:
            print(args.suite, count, "cases", flush=True)
    metrics = {k: summarize(v) for k, v in grouped.items()}
    write_json(out / "metrics.json", metrics)
    write_json(out / "target_comparison.json", targets(metrics))
    write_json(out / "case_metrics.json", case_metrics)
    write_json(
        out / "failures.json",
        {
            k: [
                r
                for r in v
                if r["wrong_exclusion"]
                or r["horizontal_error_m"] is None
                or r["horizontal_error_m"] > 10
            ]
            for k, v in grouped.items()
            if k.startswith("all/")
        },
    )
    manifest.update(
        cases=count,
        max_baseline_numeric_difference=baseline_difference,
        course_contract_violations=violations,
    )
    write_json(out / "manifest.json", manifest)
    print(
        json.dumps(
            {k: v for k, v in metrics.items() if k.startswith("all/") or k.endswith("/new")},
            indent=2,
        ),
        flush=True,
    )
    assert violations == 0 and baseline_difference < 1e-4


if __name__ == "__main__":
    main()
