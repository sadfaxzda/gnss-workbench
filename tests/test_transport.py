import json
import socket
import threading
import time
from dataclasses import asdict

import pytest

from gnss_workbench.io import read_epochs
from gnss_workbench.settings import COURSE_ROOT
from gnss_workbench.worker import MAX_LINE_BYTES, tcp_frames


def server_sends(payloads):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def run():
        with server, server.accept()[0] as connection:
            for payload in payloads:
                if isinstance(payload, float):
                    time.sleep(payload)
                else:
                    try:
                        connection.sendall(payload)
                    except BrokenPipeError:
                        break

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return port, thread


def test_split_packets_pause_resume_end_and_empty_epochs():
    epochs = list(read_epochs(COURSE_ROOT / "data/D03_sim_demo.jsonl"))
    frames = [{"type": "meta", "replay_interval_wall_s": 0.01}]
    frames += [{"type": "epoch", **asdict(epochs[i])} for i in [1, 460, 520]]
    data = ("\n".join(json.dumps(f) for f in frames) + "\n").encode()
    end = b'{"type":"end","epochs_sent":3}\n'
    port, thread = server_sends([data[:17], data[17:49], data[49:], 3.3, end])
    events = list(tcp_frames(port, threading.Event()))
    assert [e["epoch_id"] for e in events if e["type"] == "epoch"] == [1, 460, 520]
    assert [e["status"] for e in events if e["type"] == "transport"] == [
        "TRANSPORT_CONNECTED",
        "TRANSPORT_STALE",
        "TRANSPORT_RESUMED",
        "TRANSPORT_ENDED",
    ]
    thread.join(timeout=1)


def test_unexpected_disconnect_is_not_success():
    port, thread = server_sends([b'{"type":"meta"}\n'])
    with pytest.raises(ValueError, match="end"):
        list(tcp_frames(port, threading.Event()))
    thread.join(timeout=1)


def test_oversize_partial_frame_rejected():
    port, thread = server_sends([b"x" * (MAX_LINE_BYTES + 1)])
    with pytest.raises(ValueError, match="1 MiB"):
        list(tcp_frames(port, threading.Event()))
    thread.join(timeout=1)


def test_file_and_fragmented_tcp_use_identical_solutions():
    from gnss_workbench.core.models import Epoch
    from gnss_workbench.core.solver import PositioningEngine
    from gnss_workbench.io import csv_row, navigation_from

    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    file_epochs = list(read_epochs(COURSE_ROOT / "data/D03_sim_demo.jsonl"))
    selected = [file_epochs[i] for i in [70, 170, 330, 460, 500, 520, 550]]
    data = (
        "\n".join(json.dumps({"type": "epoch", **asdict(epoch)}) for epoch in selected)
        + '\n{"type":"end","epochs_sent":7}\n'
    ).encode()
    port, thread = server_sends([data[:19], data[19:150], data[150:]])
    engine_file, engine_tcp = PositioningEngine(nav), PositioningEngine(nav)
    streamed = [
        Epoch.from_dict(frame, tolerate_observation_errors=True)
        for frame in tcp_frames(port, threading.Event())
        if frame["type"] == "epoch"
    ]
    for file_epoch, tcp_epoch in zip(selected, streamed, strict=True):
        for file_result, tcp_result in zip(
            engine_file.solve(file_epoch), engine_tcp.solve(tcp_epoch), strict=True
        ):
            file_row, tcp_row = csv_row(file_result), csv_row(tcp_result)
            file_row.pop("processing_ms")
            tcp_row.pop("processing_ms")
            assert file_row == tcp_row
    thread.join(timeout=1)


def test_causal_diagnosis_depends_on_gpst_not_packet_timing():
    from dataclasses import replace

    from gnss_workbench.core.models import Epoch
    from gnss_workbench.core.solver import PositioningEngine
    from gnss_workbench.io import navigation_from

    nav = navigation_from(COURSE_ROOT / "data/navigation.json")
    source = list(read_epochs(COURSE_ROOT / "data/D02_sim_clean.jsonl"))[:30]
    epochs = [
        replace(
            e,
            observations=tuple(
                replace(o, pseudorange_m=o.pseudorange_m - (30 if o.sat_id == "G07" else 0))
                for o in e.observations[:6]
            ),
        )
        for e in source
    ]
    payload = (
        "\n".join(json.dumps({"type": "epoch", **asdict(e)}) for e in epochs)
        + '\n{"type":"end","epochs_sent":30}\n'
    ).encode()
    port, thread = server_sends([payload[:73], payload[73:800], payload[800:]])
    batch, live = PositioningEngine(nav), PositioningEngine(nav)
    received = [
        Epoch.from_dict(f) for f in tcp_frames(port, threading.Event()) if f["type"] == "epoch"
    ]
    accumulated = False
    for left, right in zip(epochs, received, strict=True):
        for a, b in zip(batch.solve(left), live.solve(right), strict=True):
            first, second = a.to_dict(), b.to_dict()
            first.pop("processing_ms")
            second.pop("processing_ms")
            assert first == second
            accumulated |= any(
                c.get("selection_method") == "causal_likelihood" for c in a.candidate_scores
            )
    assert accumulated
    thread.join(timeout=1)
