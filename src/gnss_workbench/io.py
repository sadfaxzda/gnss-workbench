"""Streaming source adapters and course-compatible result export."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .core.models import CSV_FIELDS, Epoch, Solution


def read_frames(path: Path) -> Iterator[dict[str, Any]]:
    seen: set[int] = set()
    with path.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            if len(line.encode("utf-8")) > 1024 * 1024:
                raise ValueError("Frame exceeds 1 MiB")
            try:
                frame = json.loads(line)
            except json.JSONDecodeError as error:
                raise json.JSONDecodeError(
                    f"观测文件第 {line_number} 行 JSON 格式错误：{error.msg}", line, error.pos
                ) from error
            if not isinstance(frame, dict):
                raise ValueError("Each frame must be a JSON object")
            if frame.get("type") == "meta":
                continue
            epoch = Epoch.from_dict(frame, tolerate_observation_errors=True)
            if epoch.epoch_id in seen:
                raise ValueError(f"Duplicate epoch_id: {epoch.epoch_id}")
            seen.add(epoch.epoch_id)
            yield frame


def read_epochs(path: Path) -> Iterator[Epoch]:
    for frame in read_frames(path):
        yield Epoch.from_dict(frame, tolerate_observation_errors=True)


def validate_navigation(nav: dict[str, Any]) -> dict[str, Any]:
    if nav.get("schema") != "GNSS-COURSE-NAV-1.0":
        raise ValueError("Unsupported navigation schema")
    try:
        for key in ("alpha", "beta"):
            if len(nav[key]) != 4 or not all(math.isfinite(v) for v in nav[key]):
                raise ValueError("Ionosphere coefficients must be four finite numbers")
        required = (
            "toc",
            "toc_week",
            "af0",
            "af1",
            "af2",
            "crs",
            "delta_n",
            "m0",
            "cuc",
            "e",
            "cus",
            "sqrt_a",
            "toe",
            "cic",
            "omega0",
            "cis",
            "i0",
            "crc",
            "omega",
            "omega_dot",
            "idot",
            "gps_week",
            "tgd",
            "sv_health",
        )
        if not nav["ephemerides"]:
            raise ValueError("No broadcast ephemerides")
        for eph in nav["ephemerides"].values():
            if not all(math.isfinite(eph[key]) for key in required):
                raise ValueError("Ephemeris values must be finite")
            if not 0 <= eph["e"] < 1 or not 4000 < eph["sqrt_a"] < 6000:
                raise ValueError("Ephemeris orbit is outside GPS broadcast model")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"Malformed navigation: {error}") from error
    return nav


def navigation_from(path: Path) -> dict[str, Any]:
    return validate_navigation(json.loads(path.read_text(encoding="utf-8-sig")))


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
