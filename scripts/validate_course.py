"""Independent course evaluation and broadcast checkpoint evidence."""

import csv
import json
import time
from pathlib import Path

import numpy as np

from gnss_workbench.core.ephemeris import satellite_state
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.evaluation import evaluate_run
from gnss_workbench.io import export_solutions, navigation_from, read_epochs
from gnss_workbench.settings import COURSE_ROOT

nav = navigation_from(COURSE_ROOT / "data/navigation.json")
with (COURSE_ROOT / "reference/satellite_checkpoints.csv").open() as stream:
    checks = list(csv.DictReader(stream))
error = max(
    np.linalg.norm(
        satellite_state(nav["ephemerides"][r["sat_id"]], float(r["gps_sow_tx"]))[0]
        - [float(r[k]) for k in ["x_tx_m", "y_tx_m", "z_tx_m"]]
    )
    for r in checks
)
print("checkpoints_max_position_m", error, flush=True)
for name in ["D02_sim_clean", "D03_sim_demo", "D01_real_excerpt"]:
    engine = PositioningEngine(nav)
    started = time.monotonic()
    baseline, improved = [], []
    for epoch in read_epochs(COURSE_ROOT / "data" / f"{name}.jsonl"):
        b, i = engine.solve(epoch)
        baseline.append(b)
        improved.append(i)
    out = Path("runtime/verification") / name
    export_solutions(out / "baseline.csv", baseline)
    export_solutions(out / "improved.csv", improved)
    print(
        name,
        "seconds",
        time.monotonic() - started,
        "statuses",
        sorted({s.status for s in improved}),
        flush=True,
    )
    if name != "D01_real_excerpt":
        metrics = evaluate_run(
            COURSE_ROOT / "data" / f"{name}.jsonl",
            COURSE_ROOT / "reference" / f"{name}_truth.csv",
            out,
        )
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        print(json.dumps(metrics, indent=2), flush=True)
