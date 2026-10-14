"""Streaming source adapters and course-compatible result export."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .core.models import CSV_FIELDS, Epoch, Solution


def read_epochs(path: Path) -> Iterator[Epoch]:
    seen: set[int] = set()
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.strip():
                continue
            frame = json.loads(line)
            if frame.get("type") == "meta":
                continue
            epoch = Epoch.from_dict(frame)
            if epoch.epoch_id in seen:
                raise ValueError(f"Duplicate epoch_id: {epoch.epoch_id}")
            seen.add(epoch.epoch_id)
            yield epoch


def navigation_from(path: Path) -> dict[str, Any]:
    nav = json.loads(path.read_text(encoding="utf-8"))
    if nav.get("schema") != "GNSS-COURSE-NAV-1.0":
        raise ValueError("Unsupported navigation schema")
    return nav


def csv_row(solution: Solution) -> dict[str, Any]:
    result = solution.to_dict()
    result["flagged_sats"] = ";".join(solution.flagged_sats)
    result["excluded_sats"] = ";".join(solution.excluded_sats)
    return {key: result[key] for key in CSV_FIELDS}


def export_solutions(path: Path, solutions: list[Solution]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(s) for s in solutions)
