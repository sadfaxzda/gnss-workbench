"""Post-run evaluation only. Reference truth never enters the solver."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .settings import COURSE_ROOT


def evaluate_run(input_path: Path, truth_path: Path, output_dir: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "course_evaluator", COURSE_ROOT / "tools" / "evaluate.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Course evaluator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = {}
    for mode in ("baseline", "improved"):
        metrics = module.evaluate(input_path, truth_path, output_dir / f"{mode}.csv")
        result[mode] = {
            key: value
            for key, value in metrics.items()
            if key not in {"per_epoch", "contract_violations"}
        }
    return result
