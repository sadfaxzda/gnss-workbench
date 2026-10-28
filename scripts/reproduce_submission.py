"""Reproduce public cases, ablation and a six-satellite limitation without UI."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def reproduce(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Output directory must be empty; choose a new --out path")
    out.mkdir(parents=True, exist_ok=True)
    course = ROOT / "fixtures/course"
    for dataset, disabled in [
        ("D01_real_excerpt", False),
        ("D02_sim_clean", False),
        ("D03_sim_demo", False),
        ("D03_sim_demo", True),
    ]:
        name = dataset + ("_ablation" if disabled else "")
        command = [
            sys.executable,
            "-m",
            "gnss_workbench.cli",
            "solve",
            "--input",
            str(course / "data" / f"{dataset}.jsonl"),
            "--out",
            str(out / name),
        ]
        truth = course / "reference" / f"{dataset}_truth.csv"
        if truth.is_file():
            command += ["--truth", str(truth)]
        if disabled:
            command.append("--disable-fde")
        subprocess.run(command, cwd=ROOT, check=True)

    # An explicit experiment input; these labels are never passed to the solver.
    inputs = out / "six_satellite_input"
    inputs.mkdir()
    lines = (course / "data/D02_sim_clean.jsonl").read_text(encoding="utf-8").splitlines()
    frames = [json.loads(line) for line in lines[1:36]]
    for frame in frames:
        frame["observations"] = frame["observations"][:6]
        for observation in frame["observations"]:
            if observation["sat_id"] == "G07":
                observation["pseudorange_m"] -= 30.0
    input_path = inputs / "observations.jsonl"
    input_path.write_text(
        lines[0] + "\n" + "\n".join(json.dumps(frame) for frame in frames) + "\n",
        encoding="utf-8",
    )
    truth_path = inputs / "truth.csv"
    with (course / "reference/D02_sim_clean_truth.csv").open(encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)[:35]
        fields = reader.fieldnames
    for row in rows:
        row.update(fault_sat="G07", fault_bias_m="-30.0", event="six_satellite_cold_start")
    with truth_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or [])
        writer.writeheader()
        writer.writerows(rows)
    (inputs / "README.txt").write_text(
        "Derived from D02 epochs 0..34. Retain the first six observations in file order; "
        "add -30 m to G07. Truth positions and clocks are unchanged. "
        "This public-data derivative demonstrates a known limitation, not a held-out test.\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "gnss_workbench.cli",
            "solve",
            "--input",
            str(input_path),
            "--truth",
            str(truth_path),
            "--out",
            str(out / "six_satellite_limit"),
        ],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    reproduce(parser.parse_args().out.resolve())
