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
