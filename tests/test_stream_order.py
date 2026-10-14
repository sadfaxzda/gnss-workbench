"""Exercise a worker finishing while the socket yields to send a batch."""

import asyncio
import json
from collections import deque
from types import SimpleNamespace

from gnss_workbench.api import create_app


def test_terminal_status_waits_for_epochs_added_during_send(tmp_path):
    app = create_app(tmp_path)
    run = {"status": "running", "epoch_count": 0}
    log = deque()
    sequence = {"finishing": 0}
    app.state.manager = SimpleNamespace(
        get=lambda _: dict(run),
        history_batches=lambda _id, _count: iter([]),
        events={"finishing": log},
        sequence=sequence,
        transport={},
        position_stale={},
    )
    messages = []

    def append_event(event):
        sequence["finishing"] += 1
        log.append({**event, "seq": sequence["finishing"], "schema": "gnss-stream/1"})

    class FinishingSocket:
        headers = {"host": "testserver"}
        close_code = None

        async def accept(self):
            pass

        async def send_json(self, message):
            messages.append(message)
            if message["type"] == "snapshot":
                append_event({"type": "epoch", "epoch_id": 0})

        async def send_text(self, message):
            event = json.loads(message)
            messages.append(event)
            if event.get("epoch_id") == 0:
                # The pump can finish while an awaited socket send is in progress.
                append_event({"type": "epoch", "epoch_id": 1})
                append_event({"type": "complete", "status": "completed"})
                run.update(status="completed", epoch_count=2)
                await asyncio.sleep(0)

        async def close(self, code):
            self.close_code = code

    stream = next(route.endpoint for route in app.routes if route.path.endswith("/stream"))
    socket = FinishingSocket()
    asyncio.run(stream(socket, "finishing"))

    assert [m["epoch_id"] for m in messages if m["type"] == "epoch"] == [0, 1]
    assert messages[-1]["type"] == "run_status"
    assert messages[-1]["run"]["epoch_count"] == 2
    assert socket.close_code == 1000
