"""Single-owner run lifecycle and durable history, independent of web clients."""

from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import queue
import uuid
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import RunRequest
from .persistence import RunStore
from .worker import run_worker


class RunManager:
    def __init__(self, root: Path):
        self.root = root
        self.store = RunStore(root)
        self.active: dict[str, dict[str, Any]] = {}
        self.events: dict[str, deque] = {}
        self.sequence: dict[str, int] = {}
        self.transport: dict[str, str] = {}

    def create(self, request: RunRequest) -> dict[str, Any]:
        if self.active:
            raise ValueError("已有运行中的任务，请先停止或等待完成")
        run_id = uuid.uuid4().hex
        output = self.root / "runs" / run_id
        output.mkdir(parents=True)
        self.store.create(run_id, datetime.now(UTC).isoformat(), request.model_dump())
        context = mp.get_context("spawn")
        event_queue = context.Queue(maxsize=1000)
        stop = context.Event()
        process = context.Process(
            target=run_worker,
            args=(run_id, request.model_dump(), str(output), event_queue, stop),
            daemon=True,
        )
        self.events[run_id] = deque(maxlen=2000)
        self.sequence[run_id] = 0
        self.active[run_id] = {"process": process, "queue": event_queue, "stop": stop, "count": 0}
        process.start()
        self.active[run_id]["task"] = asyncio.create_task(self._pump(run_id))
        return self.store.get(run_id) or {}

    async def _pump(self, run_id: str) -> None:
        active = self.active[run_id]
        process = active["process"]
        terminal = False
        dead_polls = 0
        while not terminal:
            received = False
            while True:
                try:
                    event = active["queue"].get_nowait()
                except queue.Empty:
                    break
                received = True
                self.sequence[run_id] += 1
                event.update(seq=self.sequence[run_id], schema="gnss-stream/1", run_id=run_id)
                self.events[run_id].append(event)
                if event["type"] == "transport":
                    self.transport[run_id] = event["status"]
                if event["type"] == "epoch":
                    active["count"] += 1
                    if active["count"] % 10 == 0:
                        self.store.update(run_id, epoch_count=active["count"])
                elif event["type"] == "complete":
                    self.store.update(
                        run_id,
                        status=event["status"],
                        epoch_count=event["epoch_count"],
                        summary=event["summary"],
                        error=event.get("error"),
                    )
                    terminal = True
            if not process.is_alive() and not received and not terminal:
                dead_polls += 1
                if dead_polls >= 5:
                    self.store.update(
                        run_id,
                        status="failed",
                        epoch_count=active["count"],
                        error=f"计算进程意外退出 ({process.exitcode})",
                    )
                    terminal = True
            else:
                dead_polls = 0
            if not terminal:
                await asyncio.sleep(0.025)
        await asyncio.to_thread(process.join, 2)
        if process.is_alive():
            process.terminate()
            await asyncio.to_thread(process.join, 2)
        active["queue"].close()
        self.active.pop(run_id, None)

    def stop(self, run_id: str) -> None:
        if run_id in self.active:
            self.active[run_id]["stop"].set()
            self.store.update(run_id, status="stopping")

    def get(self, run_id: str) -> dict[str, Any] | None:
        result = self.store.get(run_id)
        if result and run_id in self.active:
            result["epoch_count"] = self.active[run_id]["count"]
        return result

    def history(self, run_id: str, offset: int = 0, limit: int = 5000) -> list[dict[str, Any]]:
        path = self.root / "runs" / run_id / "epochs.jsonl"
        if not path.exists():
            return []
        result = []
        with path.open(encoding="utf-8") as stream:
            for index, line in enumerate(stream):
                if index < offset:
                    continue
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    # A concurrent writer may not have completed its final line yet.
                    break
                if len(result) >= limit:
                    break
        return result

    async def close(self) -> None:
        for run_id in list(self.active):
            self.stop(run_id)
        tasks = [a["task"] for a in self.active.values()]
        if tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=8)
            except TimeoutError:
                for run_id, active in list(self.active.items()):
                    active["process"].terminate()
                    active["process"].join(timeout=2)
                    self.store.update(run_id, status="interrupted", error="服务关闭时终止计算进程")
        self.store.close()
