"""Reproducible low-redundancy development/held-out/isolated fault comparison.

Run from the repository root. Inputs, truth, configurations, CSVs, diagnostics,
failures and input/source hashes are saved in a new output directory. No output
epochs, ambiguous results or wrong exclusions are removed from the denominator.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from itertools import combinations
from pathlib import Path

import numpy as np

from gnss_workbench.core.coordinates import local_enu
from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.evaluation import evaluate_run
from gnss_workbench.io import export_solutions, navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT, PROJECT_ROOT


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def scenarios(suite, epochs, seed):
    rng = np.random.default_rng(seed)
    for n in (6, 7):
        groups = [tuple(range(n))] if suite == "dev" else list(combinations(range(8), n))
        for group_index, indices in enumerate(groups):
            if suite == "cold":
                choices = [(target, sign, "isolated") for target in indices for sign in (-1, 1)]
            elif suite == "dev":
                choices = [(target, sign, "step") for target in indices for sign in (-1, 1)]
            else:
                choices = [
                    (int(rng.choice(indices)), sign, "step" if sign == -1 else "ramp")
                    for sign in (-1, 1)
                ]
                choices += [(indices[0], 1, kind) for kind in ("clean", "common", "switch")]
            for target, sign, kind in choices:
                start = 0 if suite == "dev" else int(rng.integers(300, 520))
                length = 1 if kind == "isolated" else 30 if kind in {"clean", "common"} else 80
                amplitude = 30.0 if suite == "dev" else float(rng.choice([30, 45, 80, 120]))
                frames, labels = [], []
                for t in range(length):
                    original = epochs[start + t]
                    active = kind == "isolated" or (
                        kind in {"step", "ramp", "switch"} and 10 <= t < 70
                    )
                    actual_target = target
                    if kind == "switch" and t >= 40:
                        actual_target = indices[1]
                    bias = sign * amplitude if active else 0.0
                    if active and kind == "ramp":
                        bias *= (t - 9) / 60
                    common = 100.0 if kind == "common" and 5 <= t < 25 else 0.0
                    noise = np.zeros(n) if suite == "dev" else rng.normal(0, 0.25, n)
                    observations = tuple(
                        replace(
                            original.observations[index],
                            pseudorange_m=original.observations[index].pseudorange_m
                            + common
                            + (bias if index == actual_target else 0)
                            + float(noise[j]),
                        )
                        for j, index in enumerate(indices)
                    )
                    frames.append(replace(original, epoch_id=t, observations=observations))
                    labels.append(
                        {
                            "original_epoch_id": original.epoch_id,
                            "satellite": original.observations[actual_target].sat_id
                            if active
                            else "",
                            "bias_m": bias,
                            "common_m": common,
                        }
                    )
                name = f"n{n}-set{group_index:02}-{target}-{sign}-{kind}"
                yield name, n, kind, frames, labels


def summarize(records):
    errors = [r["horizontal_error_m"] for r in records if r["horizontal_error_m"] is not None]
    faults = [r for r in records if r["fault_satellite"] and abs(r["bias_m"]) >= 30]
    clean = [r for r in records if not r["fault_satellite"]]
    fault_errors = [r["horizontal_error_m"] for r in faults if r["horizontal_error_m"] is not None]
    return {
        "epochs": len(records),
        "position_availability": len(errors) / len(records),
        "h_p95_m": float(np.percentile(errors, 95)) if errors else None,
        "success_within_10m": sum(e <= 10 for e in errors) / len(records),
        "strong_fault_epochs": len(faults),
        "strong_fault_recall": sum(r["detected"] for r in faults) / len(faults) if faults else None,
        "fault_only_h_p95_m": float(np.percentile(fault_errors, 95)) if fault_errors else None,
        "fault_only_success_within_10m": sum(e <= 10 for e in fault_errors) / len(faults)
        if faults
        else None,
        "wrong_exclusion_rate": sum(r["wrong_exclusion"] for r in records) / len(records),
        "clean_flag_rate": sum(bool(r["flagged"]) for r in clean) / len(clean) if clean else None,
        "suspect_rate": sum(r["status"] == "SUSPECT" for r in records) / len(records),
        "clock_p95_m": float(
            np.percentile(
                [r["clock_error_m"] for r in records if r["clock_error_m"] is not None], 95
            )
        ),
        "processing_p95_ms": float(np.percentile([r["processing_ms"] for r in records], 95)),
        "statuses": dict(Counter(r["status"] for r in records)),
    }


def target_comparison(metrics):
    """Expose unmet numerical targets separately from a successful script exit."""
    comparison = {}
    for n in (6, 7):
        row = metrics[f"n{n}/causal_likelihood"]
        checks = {
            "h_p95_le_10m": row["h_p95_m"] is not None and row["h_p95_m"] <= 10,
            "joint_success_ge_95pct": row["success_within_10m"] >= 0.95,
            "strong_fault_recall_ge_90pct": row["strong_fault_recall"] is not None
            and row["strong_fault_recall"] >= 0.90,
            "clean_false_alarm_le_5pct": row["clean_flag_rate"] <= 0.05
            if row["clean_flag_rate"] is not None
            else None,
        }
        comparison[f"n{n}"] = {
            "checks": checks,
            "all_measured_targets_met": False not in checks.values(),
        }
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["dev", "validation", "cold"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--seed", type=int, help="New independent generation seed; saved in manifest"
    )
    args = parser.parse_args()
    seed = (
        args.seed if args.seed is not None else 2026101702 if args.suite == "cold" else 2026101701
    )
    out = args.out
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Choose a new output directory to preserve evidence")
    out.mkdir(parents=True, exist_ok=True)
    source = COURSE_ROOT / "data/D02_sim_clean.jsonl"
    navigation = COURSE_ROOT / "data/navigation.json"
    epochs = list(read_epochs(source))
    nav = navigation_from(navigation)
    with (COURSE_ROOT / "reference/D02_sim_clean_truth.csv").open(encoding="utf-8") as stream:
        truth = list(csv.DictReader(stream))
    configurations = {
        "original": SolverConfig(resolve_ambiguity=False),
        "snapshot_likelihood": SolverConfig(fde_history_epochs=1),
        "causal_likelihood": SolverConfig(),
    }
    (out / "navigation.json").write_bytes(navigation.read_bytes())
    manifest = {
        "suite": args.suite,
        "seed": seed,
        "scope": "Supplied D02 geometry with new observation subsets, fault targets, bias/noise and times. Not teacher hidden cases or external field validation.",
        "configurations": {name: asdict(config) for name, config in configurations.items()},
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "navigation_sha256": hashlib.sha256(navigation.read_bytes()).hexdigest(),
        "code_sha256": {
            str(p.relative_to(PROJECT_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (PROJECT_ROOT / "src/gnss_workbench/core").glob("*.py")
        },
        "inputs": {},
    }
    grouped = defaultdict(list)
    delays = defaultdict(list)
    max_baseline_difference = 0.0
    contract_violations = 0
    case_count = 0
    for name, n, kind, frames, labels in scenarios(args.suite, epochs, seed):
        case_count += 1
        folder = out / name
        folder.mkdir()
        input_path = folder / "input.jsonl"
        input_path.write_text(
            json.dumps({"type": "meta", "schema": "GNSS-COURSE-1.0"})
            + "\n"
            + "".join(json.dumps({"type": "epoch", **asdict(e)}) + "\n" for e in frames),
            encoding="utf-8",
        )
        manifest["inputs"][name] = hashlib.sha256(input_path.read_bytes()).hexdigest()
        truth_path = folder / "truth.csv"
        with truth_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(truth[0]))
            writer.writeheader()
            for frame, label in zip(frames, labels, strict=True):
                row = truth[label["original_epoch_id"]].copy()
                row.update(
                    epoch_id=frame.epoch_id,
                    fault_sat=label["satellite"],
                    fault_bias_m=label["bias_m"],
                    common_bias_m=label["common_m"],
                    clock_bias_m=float(row["clock_bias_m"]) + label["common_m"],
                    event=kind,
                )
                writer.writerow(row)
        reference_baselines = []
        for method, config in configurations.items():
            engine = PositioningEngine(nav, config)
            destination = folder / method
            destination.mkdir()
            baseline, solutions, records = [], [], []
            with (destination / "diagnostics.jsonl").open("w", encoding="utf-8") as logs:
                for epoch, label in zip(frames, labels, strict=True):
                    b, s = engine.solve(epoch)
                    baseline.append(b)
                    solutions.append(s)
                    logs.write(json.dumps(s.to_dict(), ensure_ascii=False, allow_nan=False) + "\n")
                    ref = truth[label["original_epoch_id"]]
                    xyz = np.array([float(ref[k]) for k in ("x_m", "y_m", "z_m")])
                    error = (
                        float(np.linalg.norm(local_enu(np.array([s.x_m, s.y_m, s.z_m]), xyz)[:2]))
                        if s.has_position
                        else None
                    )
                    records.append(
                        {
                            "case": name,
                            "epoch_id": epoch.epoch_id,
                            "gps_sow": epoch.gps_sow,
                            "horizontal_error_m": error,
                            "clock_error_m": abs(
                                s.clock_bias_m - float(ref["clock_bias_m"]) - label["common_m"]
                            )
                            if s.clock_bias_m is not None
                            else None,
                            "fault_satellite": label["satellite"],
                            "bias_m": label["bias_m"],
                            "flagged": s.flagged_sats,
                            "excluded": s.excluded_sats,
                            "detected": bool(
                                label["satellite"] and label["satellite"] in s.flagged_sats
                            ),
                            "wrong_exclusion": bool(set(s.excluded_sats) - {label["satellite"]}),
                            "status": s.status,
                            "processing_ms": s.processing_ms,
                        }
                    )
            export_solutions(destination / "baseline.csv", baseline)
            export_solutions(destination / "improved.csv", solutions)
            metrics = evaluate_run(input_path, truth_path, destination)
            contract_violations += sum(m["contract_violation_count"] for m in metrics.values())
            write_json(destination / "course_metrics.json", metrics)
            write_json(destination / "evaluation.json", records)
            if method == "original":
                reference_baselines = baseline
            else:
                for left, right in zip(reference_baselines, baseline, strict=True):
                    assert left.status == right.status and left.n_used == right.n_used
                    if left.has_position:
                        delta = max(
                            abs(getattr(left, k) - getattr(right, k))
                            for k in ("x_m", "y_m", "z_m", "clock_bias_m", "pdop", "residual_rms_m")
                        )
                        max_baseline_difference = max(max_baseline_difference, delta)
            grouped[f"n{n}/{method}"].extend(records)
            grouped[f"n{n}/{kind}/{method}"].extend(records)
            # Each strong-fault segment is measured from its first strong epoch.
            previous = None
            for index, record in enumerate(records):
                identity = record["fault_satellite"] if abs(record["bias_m"]) >= 30 else None
                if identity and identity != previous:
                    end = index + 1
                    while (
                        end < len(records)
                        and records[end]["fault_satellite"] == identity
                        and abs(records[end]["bias_m"]) >= 30
                    ):
                        end += 1
                    first = next(
                        (
                            r["gps_sow"] - record["gps_sow"]
                            for r in records[index:end]
                            if r["detected"]
                        ),
                        None,
                    )
                    delays[f"n{n}/{method}"].append(first)
                previous = identity
        if case_count % 12 == 0:
            print(f"{args.suite}: {case_count} cases", flush=True)
    result = {key: summarize(records) for key, records in grouped.items()}
    for key, values in delays.items():
        found = [v for v in values if v is not None]
        result[key]["segments_never_detected"] = values.count(None)
        result[key]["first_detection_delay_p95_s"] = (
            float(np.percentile(found, 95)) if found else None
        )
        result[key]["first_detection_delay_max_s"] = max(found) if found else None
    failures = {
        key: [
            r
            for r in rows
            if r["wrong_exclusion"]
            or r["horizontal_error_m"] is None
            or r["horizontal_error_m"] > 10
        ]
        for key, rows in grouped.items()
        if key.count("/") == 1
    }
    write_json(out / "failures.json", failures)
    manifest.update(
        cases=case_count,
        max_baseline_numeric_difference_m=max_baseline_difference,
        course_contract_violations=contract_violations,
    )
    write_json(out / "manifest.json", manifest)
    write_json(out / "metrics.json", result)
    write_json(out / "target_comparison.json", target_comparison(result))
    print(
        json.dumps(
            {key: row for key, row in result.items() if key.count("/") == 1},
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    assert contract_violations == 0
    assert max_baseline_difference < 1e-4


if __name__ == "__main__":
    main()
