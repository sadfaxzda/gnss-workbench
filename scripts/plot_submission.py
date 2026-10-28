"""Plot truth-based D03 errors from saved solutions; never run or alter the solver."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/media/submission-error.png")
    args = parser.parse_args()
    font_candidates = [
        Path(os.environ.get("GNSS_REPORT_HEI_FONT", "C:/Windows/Fonts/simhei.ttf")),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    ]
    font = next((path for path in font_candidates if path.is_file()), None)
    if font is None:
        raise SystemExit("Set GNSS_REPORT_HEI_FONT to an installed licensed Heiti/SimHei font")
    font_manager.fontManager.addfont(str(font))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams["axes.unicode_minus"] = False
    spec = importlib.util.spec_from_file_location(
        "course_evaluator", ROOT / "fixtures/course/tools/evaluate.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Course evaluator unavailable")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)

    def rows(path):
        with path.open(encoding="utf-8") as stream:
            return {int(row["epoch_id"]): row for row in csv.DictReader(stream)}

    truth = rows(ROOT / "fixtures/course/reference/D03_sim_demo_truth.csv")
    fig, ax = plt.subplots(figsize=(9.6, 3.15), layout="constrained")
    for mode, label, color in (
        ("baseline", "Baseline OLS", "#555555"),
        ("improved", "Improved", "#005A8D"),
    ):
        data = rows(args.results / "D03_sim_demo" / f"{mode}.csv")
        epochs = sorted(data)
        errors = [
            evaluator.enu_error(
                [float(truth[n][k]) for k in ("x_m", "y_m", "z_m")],
                [float(data[n][k]) for k in ("x_m", "y_m", "z_m")],
            )[0]
            if data[n]["x_m"]
            else np.nan
            for n in epochs
        ]
        ax.plot(epochs, errors, label=label, color=color, linewidth=1.15)
    for lo, hi, label, color in (
        (120, 179, "G19 +80 m", "#E9EDF1"),
        (300, 359, "All +100 m", "#E9EDF1"),
        (420, 439, "4 SV", "#EFEFEF"),
        (460, 479, "3 SV", "#E3E3E3"),
        (520, 529, "0 SV", "#E3E3E3"),
    ):
        ax.axvspan(lo - 0.5, hi + 0.5, color=color, zorder=0)
        ax.text((lo + hi) / 2, 28.2, label, ha="center", va="top", fontsize=8)
    ax.axhline(10, color="#888888", linestyle="--", linewidth=0.8, label="10 m reference")
    ax.set(xlabel="Epoch ID (1 Hz)", ylabel="Horizontal error (m)", xlim=(0, 599), ylim=(0, 31))
    ax.set_xticks(range(0, 601, 100))
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.5)
    ax.legend(loc="upper right", bbox_to_anchor=(1, 1.22), ncol=3, frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=240, facecolor="white")
    plt.close(fig)
    print(args.out)


if __name__ == "__main__":
    main()
