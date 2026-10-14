"""A supervised compute process. Browser connection lifetime cannot own a run."""

from __future__ import annotations

import csv
import hashlib
import json
import socket
import time
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .contracts import RunRequest
from .core.coordinates import geodetic, local_enu
from .core.models import CSV_FIELDS, Epoch, SolverConfig
from .core.solver import PositioningEngine
from .evaluation import evaluate_run
from .experiments import inject
from .io import csv_row, navigation_from, read_frames
from .provenance import source_revision
from .settings import COURSE_ROOT

MAX_LINE_BYTES = 1024 * 1024


def tcp_frames(port: int, stop: Any) -> Iterator[dict[str, Any]]:
    """LF framing handles fragmented/coalesced packets and explicit end frames."""
    with socket.create_connection(("127.0.0.1", port), timeout=5) as stream:
        stream.settimeout(0.25)
        buffer = bytearray()
        last_received = time.monotonic()
        stale = False
        timeout = 3.0
        count = 0
        seen = set()
        yield {"type": "transport", "status": "TRANSPORT_CONNECTED"}
        while not stop.is_set():
            try:
                chunk = stream.recv(65536)
            except TimeoutError:
                if not stale and time.monotonic() - last_received > timeout:
                    stale = True
                    yield {"type": "transport", "status": "TRANSPORT_STALE"}
                continue
            if not chunk:
                raise ValueError("TCP 连接意外断开，未收到 end 结束帧")
            if stale:
                yield {"type": "transport", "status": "TRANSPORT_RESUMED"}
                stale = False
            last_received = time.monotonic()
            buffer.extend(chunk)
            while b"\n" in buffer:
                line, _, rest = buffer.partition(b"\n")
                buffer = bytearray(rest)
                if len(line) > MAX_LINE_BYTES:
                    raise ValueError("TCP frame exceeds 1 MiB")
                frame = json.loads(line)
                if frame.get("type") == "meta":
                    interval = float(frame.get("replay_interval_wall_s", 1.0))
                    if not np.isfinite(interval) or interval < 0:
                        raise ValueError("Invalid replay interval")
                    timeout = max(3.0, 3 * interval)
                elif frame.get("type") == "end":
                    if frame.get("epochs_sent") != count:
                        raise ValueError("TCP end count does not match received epochs")
                    yield {"type": "transport", "status": "TRANSPORT_ENDED"}
                    return
                elif frame.get("type") == "epoch":
                    epoch = Epoch.from_dict(frame, tolerate_observation_errors=True)
                    if epoch.epoch_id in seen:
                        raise ValueError("Duplicate TCP epoch_id")
                    seen.add(epoch.epoch_id)
                    count += 1
                    yield frame
                else:
                    raise ValueError("Unknown TCP frame type")
            if len(buffer) > MAX_LINE_BYTES:
                raise ValueError("TCP frame exceeds 1 MiB")


def _derived_truth(request: RunRequest, output: Path) -> Path:
    original = COURSE_ROOT / "reference" / f"{request.dataset_id}_truth.csv"
    if request.scenario.kind == "none":
        return original
    with original.open() as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        rows = list(reader)
    scenario = request.scenario
    for row in rows:
        offset = int(row["epoch_id"]) - scenario.start_epoch
        if not 0 <= offset < scenario.duration:
            continue
        bias = scenario.bias_m * ((offset + 1) / scenario.duration if scenario.ramp else 1)
        row["event"] = f"controlled_{scenario.kind}"
        if scenario.kind == "satellite_bias":
            row["fault_sat"], row["fault_bias_m"] = scenario.sat_id, str(bias)
        elif scenario.kind == "common_bias":
            row["common_bias_m"] = str(bias)
            row["clock_bias_m"] = str(float(row["clock_bias_m"]) + bias)
        elif scenario.kind == "dropout":
            n = scenario.keep_satellites
            row["expected_state"] = (
                "NO_OBSERVATIONS"
                if n == 0
                else "INVALID_INSUFFICIENT"
                if n < 4
                else "NO_REDUNDANCY"
                if n == 4
                else "POSITION_REQUIRED"
            )
    truth = output / "evaluation_truth.csv"
    with truth.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return truth


def run_worker(
    run_id: str,
    raw_request: dict[str, Any],
    output_path: str,
    queue: Any,
    stop: Any,
    source_path: str | None = None,
    navigation_path: str | None = None,
) -> None:
    request = RunRequest.model_validate(raw_request)
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    origin = None
    config = SolverConfig(
        noise_sigma_m=request.noise_sigma_m,
        false_alarm_probability=request.false_alarm_probability,
        enable_fde=request.enable_fde,
        algorithm=request.algorithm,
    )
    navigation = Path(navigation_path) if navigation_path else COURSE_ROOT / "data/navigation.json"
    source = (
        Path(source_path) if source_path else COURSE_ROOT / "data" / f"{request.dataset_id}.jsonl"
    )
    manifest = {
        "schema": "gnss-run/1",
        "run_id": run_id,
        "software_version": __version__,
        "git_revision": source_revision(),
        "request": raw_request,
        "solver": asdict(config),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()
        if request.source == "file"
        else None,
        "navigation_sha256": hashlib.sha256(navigation.read_bytes()).hexdigest(),
        "reference_truth_used_for_positioning": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "navigation.json").write_bytes(navigation.read_bytes())

    def finalize_manifest(status: str, error: str | None = None) -> None:
        saved_input = output / "input.jsonl"
        manifest.update(
            status=status,
            error=error,
            epoch_count=count,
            input_sha256=hashlib.sha256(saved_input.read_bytes()).hexdigest()
            if saved_input.is_file()
            else None,
            enu_origin_ecef=origin.tolist() if origin is not None else None,
        )
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    try:
        engine = PositioningEngine(navigation_from(navigation), config)
        frames = (
            tcp_frames(request.tcp_port, stop) if request.source == "tcp" else read_frames(source)
        )
        with (
            (output / "baseline.csv").open("w", newline="") as bfile,
            (output / "improved.csv").open("w", newline="") as ifile,
            (output / "epochs.jsonl").open("w", encoding="utf-8") as records,
            (output / "input.jsonl").open("w", encoding="utf-8") as inputs,
            (output / "events.jsonl").open("w", encoding="utf-8") as events,
        ):
            bw, iw = (
                csv.DictWriter(bfile, fieldnames=CSV_FIELDS),
                csv.DictWriter(ifile, fieldnames=CSV_FIELDS),
            )
            inputs.write(
                json.dumps(
                    {
                        "type": "meta",
                        "schema": "GNSS-COURSE-1.0",
                        "time_system": "GPST_RECEIVER_TIME_TAG",
                        "observable": "GPS_L1_C1",
                        "replay_interval_wall_s": request.interval_seconds,
                    }
                )
                + "\n"
            )
            bw.writeheader()
            iw.writeheader()
            for frame in frames:
                if stop.is_set():
                    break
                if frame["type"] == "transport":
                    event = {**frame, "wall_time": time.time()}
                    events.write(json.dumps(event) + "\n")
                    events.flush()
                    queue.put(event)
                    continue
                epoch = inject(
                    Epoch.from_dict(frame, tolerate_observation_errors=True), request.scenario
                )
                saved_frame = frame if epoch.data_error else {"type": "epoch", **asdict(epoch)}
                inputs.write(json.dumps(saved_frame) + "\n")
                baseline, improved = engine.solve(epoch)
                bw.writerow(csv_row(baseline))
                iw.writerow(csv_row(improved))
                view: dict[str, Any] = {
                    "baseline_enu": None,
                    "improved_enu": None,
                    "latitude_deg": None,
                    "longitude_deg": None,
                    "height_m": None,
                    "correction_m": None,
                }
                if origin is None and improved.has_position:
                    origin = np.array([improved.x_m, improved.y_m, improved.z_m], dtype=float)
                for mode, solution in [("baseline", baseline), ("improved", improved)]:
                    if solution.has_position and origin is not None:
                        xyz = np.array([solution.x_m, solution.y_m, solution.z_m], dtype=float)
                        view[f"{mode}_enu"] = local_enu(xyz, origin).tolist()
                        if mode == "improved":
                            lat, lon, h = geodetic(xyz)
                            view.update(
                                latitude_deg=np.degrees(lat),
                                longitude_deg=np.degrees(lon),
                                height_m=h,
                            )
                if baseline.has_position and improved.has_position:
                    view["correction_m"] = float(
                        np.linalg.norm(
                            np.array([baseline.x_m, baseline.y_m, baseline.z_m])
                            - [improved.x_m, improved.y_m, improved.z_m]
                        )
                    )
                record = {
                    "type": "epoch",
                    "epoch_id": epoch.epoch_id,
                    "baseline": baseline.to_dict(),
                    "improved": improved.to_dict(),
                    "view": view,
                }
                records.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                for handle in (records, inputs, bfile, ifile):
                    handle.flush()
                queue.put(record)
                count += 1
                if request.source == "file" and stop.wait(request.interval_seconds):
                    break
        summary: dict[str, Any] = {
            "evaluation": None,
            "evaluation_note": "当前输入没有可用的匹配真值",
        }
        if (
            request.source == "file"
            and request.dataset_id in {"D02_sim_clean", "D03_sim_demo"}
            and not stop.is_set()
        ):
            truth = _derived_truth(request, output)
            summary["evaluation"] = evaluate_run(output / "input.jsonl", truth, output)
            summary["evaluation_note"] = "受控仿真数据；真值仅在定位完成后用于评价"
            (output / "metrics.json").write_text(
                json.dumps(summary["evaluation"], indent=2), encoding="utf-8"
            )
        finalize_manifest("stopped" if stop.is_set() else "completed")
        queue.put(
            {
                "type": "complete",
                "status": "stopped" if stop.is_set() else "completed",
                "epoch_count": count,
                "summary": summary,
            }
        )
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        try:
            finalize_manifest("failed", message)
        except OSError as archive_error:
            message += f"; 归档未完成: {archive_error}"
        queue.put(
            {
                "type": "complete",
                "status": "failed",
                "epoch_count": count,
                "summary": {},
                "error": message,
            }
        )
