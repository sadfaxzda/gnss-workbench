"""Derive report window statistics from saved CSV files using the course evaluator."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def analyze(results: Path) -> dict:
    spec = importlib.util.spec_from_file_location(
        "course_evaluator", ROOT / "fixtures/course/tools/evaluate.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Course evaluator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def rows(path: Path) -> dict:
        with path.open(encoding="utf-8") as stream:
            return {int(row["epoch_id"]): row for row in csv.DictReader(stream)}

    def error(solution: dict, truth: dict) -> float:
        return module.enu_error(
            [float(truth[k]) for k in ("x_m", "y_m", "z_m")],
            [float(solution[k]) for k in ("x_m", "y_m", "z_m")],
        )[0]

    truths = rows(ROOT / "fixtures/course/reference/D03_sim_demo_truth.csv")
    result = {}
    for mode in ("baseline", "improved"):
        solutions = rows(results / "D03_sim_demo" / f"{mode}.csv")
        for low, high, label in ((120, 179, "single_fault"), (300, 359, "common_bias")):
            ids = range(low, high + 1)
            result[f"{label}_{mode}"] = dict(
                epochs=high - low + 1,
                h_p95_m=float(np.percentile([error(solutions[n], truths[n]) for n in ids], 95)),
                clock_p95_m=float(
                    np.percentile(
                        [
                            abs(
                                float(solutions[n]["clock_bias_m"])
                                - float(truths[n]["clock_bias_m"])
                            )
                            for n in ids
                        ],
                        95,
                    )
                ),
                flagged_epochs=sum(bool(solutions[n]["flagged_sats"]) for n in ids),
            )
    solutions = rows(results / "six_satellite_limit/improved.csv")
    truths = rows(results / "six_satellite_input/truth.csv")
    result["six_satellite_limit"] = dict(
        epoch0=solutions[0],
        epoch0_horizontal_error_m=error(solutions[0], truths[0]),
        wrong_exclusions=sum(
            bool(set(row["excluded_sats"].split(";")) - {"", "G07"}) for row in solutions.values()
        ),
        confirmed_wrong_exclusions=sum(
            row["status"] == "FAULT_EXCLUDED"
            and bool(set(row["excluded_sats"].split(";")) - {"", "G07"})
            for row in solutions.values()
        ),
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(analyze(args.results), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.out)
