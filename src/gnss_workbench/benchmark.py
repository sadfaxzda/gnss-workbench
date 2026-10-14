"""Seeded stress tests: post-hoc truth access is isolated from every solver.

Perturb existing course D02 observations, not an independent real-world dataset.
Holdout seed is predeclared in docs/algorithm-plan.md and never used for tuning.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .core.coordinates import local_enu
from .core.models import Epoch, SolverConfig
from .core.solver import PositioningEngine
from .io import export_solutions, navigation_from, read_epochs
from .settings import COURSE_ROOT

Algorithm = Literal["single_fde", "consensus", "adaptive_gnc"]
FAMILIES = ("clean", "single", "ramp", "double", "common", "heavy_tail", "noise_mismatch")


def run_benchmark(out: Path, seed: int = 20261016, samples: int = 84) -> dict[str, Any]:
    if not 28 <= samples <= 600:
        raise ValueError("samples must be in 28..600")
    out.mkdir(parents=True, exist_ok=True)
    source = COURSE_ROOT / "data/D02_sim_clean.jsonl"
    epochs = list(read_epochs(source))
    navigation = navigation_from(COURSE_ROOT / "data/navigation.json")
    with (COURSE_ROOT / "reference/D02_sim_clean_truth.csv").open() as stream:
        truth = {int(row["epoch_id"]): row for row in csv.DictReader(stream)}
    rng = np.random.default_rng(seed)
    all_metrics: dict[str, Any] = {}
    configurations = {
        "ols": SolverConfig(enable_fde=False),
        **{
            name: SolverConfig(algorithm=name)
            for name in ("single_fde", "consensus", "adaptive_gnc")
        },
    }
    from itertools import combinations

    pairs = list(combinations(range(8), 2))
    for family in FAMILIES:
        directory = out / family
        directory.mkdir(exist_ok=True)
        selected = sorted(rng.choice(len(epochs), samples, replace=False))
        inputs: list[Epoch] = []
        labels: list[dict[str, Any]] = []
        for index, original_index in enumerate(selected):
            original = epochs[int(original_index)]
            faults: dict[str, float] = {}
            common = 0.0
            noise = rng.normal(0, 0.25, len(original.observations))
            if family in {"single", "ramp"}:
                target = original.observations[index % 8].sat_id
                amplitude = float(rng.choice([-1, 1]) * rng.uniform(30, 150))
                if family == "ramp":
                    amplitude = (10 + 90 * (index // 8) / max(1, (samples - 1) // 8)) * (
                        -1 if index % 2 else 1
                    )
                faults[target] = amplitude
            elif family == "double":
                for satellite in pairs[index % len(pairs)]:
                    faults[original.observations[satellite].sat_id] = float(
                        rng.choice([-1, 1]) * rng.uniform(50, 120)
                    )
            elif family == "common":
                common = float(rng.choice([-1, 1]) * rng.uniform(30, 200))
            elif family == "heavy_tail":
                noise = rng.standard_t(df=2, size=8) * 3
            elif family == "noise_mismatch":
                noise = rng.normal(0, 4, 8)
            observations = tuple(
                replace(
                    o,
                    pseudorange_m=o.pseudorange_m
                    + faults.get(o.sat_id, 0)
                    + common
                    + float(noise[i]),
                )
                for i, o in enumerate(original.observations)
            )
            inputs.append(replace(original, observations=observations))
            labels.append(
                {"faults": faults, "common_m": common, "original_epoch_id": original.epoch_id}
            )
        input_path = directory / "input.jsonl"
        input_path.write_text(
            "\n".join(json.dumps({"type": "epoch", **asdict(e)}) for e in inputs) + "\n"
        )
        (directory / "labels.json").write_text(json.dumps(labels, indent=2))
        family_metrics = {}
        for name, config in configurations.items():
            engine = PositioningEngine(navigation, config)
            results = [engine.solve(epoch)[1] for epoch in inputs]
            export_solutions(directory / f"{name}.csv", results)
            records = []
            errors, clock_errors = [], []
            success = wrong_exclusions = detected = total_faults = clean_flags = accepted = 0
            for epoch, label, solution in zip(inputs, labels, results, strict=True):
                row = truth[epoch.epoch_id]
                error = None
                if solution.has_position:
                    reference = np.array([float(row[key]) for key in ("x_m", "y_m", "z_m")])
                    enu = local_enu(
                        np.array([solution.x_m, solution.y_m, solution.z_m], dtype=float), reference
                    )
                    error = float(np.linalg.norm(enu[:2]))
                    errors.append(error)
                    clock_errors.append(
                        abs(
                            float(solution.clock_bias_m or 0)
                            - float(row["clock_bias_m"])
                            - label["common_m"]
                        )
                    )
                    success += error <= 10
                faults = label["faults"]
                strong = {sat for sat, bias in faults.items() if abs(bias) >= 30}
                total_faults += len(strong)
                detected += len(strong & set(solution.flagged_sats))
                wrong = bool(set(solution.excluded_sats) - set(faults))
                wrong_exclusions += wrong
                clean_flags += bool(solution.flagged_sats) and not faults
                accepted += solution.status in {"VALID", "FAULT_EXCLUDED"}
                records.append(
                    {
                        "epoch_id": epoch.epoch_id,
                        "horizontal_error_m": error,
                        "wrong_exclusion": wrong,
                        "status": solution.status,
                        "excluded_sats": solution.excluded_sats,
                    }
                )
            family_metrics[name] = {
                "epochs": samples,
                "position_availability": len(errors) / samples,
                "accepted_rate": accepted / samples,
                "success_within_10m": success / samples,
                "h_p95_m": float(np.percentile(errors, 95)) if errors else None,
                "clock_p95_m": float(np.percentile(clock_errors, 95)) if clock_errors else None,
                "strong_fault_recall": detected / total_faults if total_faults else None,
                "wrong_exclusion_epoch_rate": wrong_exclusions / samples,
                "clean_flag_rate": clean_flags / samples if family in {"clean", "common"} else None,
                "processing_p95_ms": float(np.percentile([s.processing_ms for s in results], 95)),
                "statuses": dict(Counter(s.status for s in results)),
            }
            (directory / f"{name}-evaluation.json").write_text(json.dumps(records, indent=2))
        all_metrics[family] = family_metrics
    report = {
        "schema": "gnss-benchmark/1",
        "seed": seed,
        "samples_per_family": samples,
        "platform": platform.platform(),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "configurations": {name: asdict(config) for name, config in configurations.items()},
        "scope": "D02 geometry with independent seeded fault choices and added noise; not external field validation",
        "metrics": all_metrics,
    }
    (out / "metrics.json").write_text(json.dumps(report, indent=2))
    lines = [
        f"# 算法压力实验（seed={seed}）",
        "",
        f"每类 {samples} 历元；位置有效包含 SUSPECT，另列接受率。所有历元保留在 10 m 成功率分母。",
        "",
        "数据：D02 原始几何/噪声 + 固定种子的新故障与附加噪声，不是独立外场验证。重尾与噪声失配是失败压力测试，没有课程达标保证。",
        "",
        "| 情景 | 方法 | 水平 P95 / m | 10 m 成功率 | 接受率 | 强故障召回 | 错剔历元率 | P95 耗时 / ms |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for family, methods in all_metrics.items():
        for name, metrics in methods.items():
            recall = metrics["strong_fault_recall"]
            recall_text = "—" if recall is None else f"{recall:.1%}"
            lines.append(
                f"| {family} | {name} | {metrics['h_p95_m']:.3f} | {metrics['success_within_10m']:.1%} | {metrics['accepted_rate']:.1%} | {recall_text} | {metrics['wrong_exclusion_epoch_rate']:.1%} | {metrics['processing_p95_ms']:.2f} |"
            )
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
