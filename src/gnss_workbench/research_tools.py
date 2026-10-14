"""Optional independent WLS implementation check against Stanford gnss_lib_py.

Atmosphere/clock/receive-frame coordinates are frozen from this application's
model. This verifies the numerical snapshot solver, not the full physical model.
"""

import importlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np

from .core.ephemeris import C, rotate_to_receive
from .core.models import SolverConfig
from .core.solver import PositioningEngine
from .io import navigation_from, read_epochs
from .settings import COURSE_ROOT


def cross_check(out: Path) -> dict:
    try:
        wls = importlib.import_module("gnss_lib_py.algorithms.snapshot").wls
    except ImportError as error:
        raise RuntimeError("Install optional tools: uv sync --group research") from error
    navigation = navigation_from(COURSE_ROOT / "data/navigation.json")
    comparisons = []
    for dataset in ("D01_real_excerpt", "D02_sim_clean", "D03_sim_demo"):
        engine = PositioningEngine(navigation, SolverConfig(enable_fde=False))
        for epoch in read_epochs(COURSE_ROOT / "data" / f"{dataset}.jsonl"):
            if dataset != "D01_real_excerpt" and epoch.epoch_id % 20:
                continue
            baseline, _ = engine.solve(epoch)
            if not baseline.has_position:
                continue
            state = np.array(
                [baseline.x_m, baseline.y_m, baseline.z_m, baseline.clock_bias_m], dtype=float
            )
            retained = {diagnostic.sat_id for diagnostic in baseline.diagnostics}
            observations = [o for o in engine._prepare(epoch) if o.sat_id in retained]
            _, residual, _, _ = engine._linearize(observations, state, epoch.gps_sow)
            satellites = np.array(
                [
                    rotate_to_receive(
                        o.satellite, (o.pseudorange + C * o.code_clock - state[3]) / C
                    )
                    for o in observations
                ]
            )
            ranges = np.linalg.norm(satellites - state[:3], axis=1)
            # P_corrected = geometric range + receiver clock + residual.
            corrected = (ranges + state[3] + residual).reshape(-1, 1)
            external = wls(
                np.zeros((4, 1)), satellites.copy(), corrected, sv_rx_time=True, tol=1e-7
            ).ravel()
            difference = float(np.linalg.norm(external - state))
            comparisons.append(
                {"dataset": dataset, "epoch_id": epoch.epoch_id, "state_difference_m": difference}
            )
    result = {
        "tool": "Stanford-NavLab/gnss_lib_py",
        "version": importlib.metadata.version("gnss-lib-py"),
        "scope": "Independent snapshot WLS only; corrections shared and frozen; not an external accuracy validation",
        "epochs": len(comparisons),
        "max_state_difference_m": max(row["state_difference_m"] for row in comparisons),
        "tolerance_m": 0.001,
        "comparisons": comparisons,
    }
    result["passed"] = result["max_state_difference_m"] < result["tolerance_m"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    if not result["passed"]:
        raise RuntimeError(
            f"Snapshot WLS cross-check exceeded tolerance: {result['max_state_difference_m']}"
        )
    return result
