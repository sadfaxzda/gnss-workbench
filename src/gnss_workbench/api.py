"""Local-first API. All live computation is delegated to supervised workers."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .contracts import DatasetImport, DatasetInfo, EpochFrame, HealthInfo, RunInfo, RunRequest
from .service import RunManager
from .settings import PROJECT_ROOT, RUNTIME_ROOT


def create_app(runtime_root: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.manager = RunManager(runtime_root or RUNTIME_ROOT)
        yield
        await application.state.manager.close()

    application = FastAPI(
        title="GNSS Workbench",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    def manager() -> RunManager:
        return application.state.manager

    def require_run(run_id: str) -> dict[str, Any]:
        run = manager().get(run_id)
        if run is None:
            raise HTTPException(404, "运行记录不存在")
        return run

    @application.get("/api/health", response_model=HealthInfo)
    def health():
        return HealthInfo(status="ok", version=__version__)

    @application.get("/api/datasets", response_model=list[DatasetInfo])
    def datasets():
        return manager().datasets.list()

    @application.post("/api/datasets", response_model=DatasetInfo, status_code=201)
    def import_dataset(request: DatasetImport):
        try:
            return manager().datasets.create(request)
        except (ValueError, KeyError, TypeError) as error:
            raise HTTPException(422, str(error)) from error

    @application.get("/api/runs", response_model=list[RunInfo])
    def runs(
        response: Response,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        query: Annotated[str, Query(max_length=100)] = "",
    ):
        query = query.strip()
        response.headers["X-Total-Count"] = str(manager().store.count(query))
        return manager().store.list(offset=offset, limit=limit, query=query)

    @application.post("/api/runs", response_model=RunInfo, status_code=201)
    async def create_run(request: RunRequest):
        try:
            return manager().create(request)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @application.get("/api/runs/{run_id}", response_model=RunInfo)
    def run(run_id: str):
        return require_run(run_id)

    @application.post("/api/runs/{run_id}/stop", response_model=RunInfo)
    async def stop_run(run_id: str):
        require_run(run_id)
        manager().stop(run_id)
        return require_run(run_id)

    @application.get("/api/runs/{run_id}/epochs", response_model=list[EpochFrame])
    def epochs(
        run_id: str,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=5000)] = 5000,
    ) -> list[dict[str, Any]]:
        require_run(run_id)
        return manager().history(run_id, offset, limit)

    @application.get("/api/runs/{run_id}/download/{artifact}")
    def download(
        run_id: str,
        artifact: Literal[
            "baseline.csv",
            "improved.csv",
            "epochs.jsonl",
            "input.jsonl",
            "navigation.json",
            "events.jsonl",
            "manifest.json",
            "metrics.json",
        ],
    ):
        info = require_run(run_id)
        if info["status"] in {"running", "stopping"}:
            raise HTTPException(409, "请等待本次运行结束后导出完整文件")
        path = manager().root / "runs" / run_id / artifact
        if not path.is_file():
            raise HTTPException(404, "此运行尚无该输出文件")
        return FileResponse(
            path,
            filename=f"{run_id[:8]}-{artifact}",
            media_type="application/octet-stream",
        )

    @application.websocket("/api/runs/{run_id}/stream")
    async def stream(websocket: WebSocket, run_id: str):
        # Browser-origin check complements loopback-only binding for local control.
        origin = websocket.headers.get("origin")
        host = websocket.headers.get("host", "")
        if origin and origin not in {f"http://{host}", f"https://{host}"}:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        if manager().get(run_id) is None:
            await websocket.close(code=1008)
            return
        try:
            # One event-loop turn: snapshot and cursor cannot race the queue pump.
            last_seq = manager().sequence.get(run_id, 0)
            snapshot_run = manager().get(run_id)
            assert snapshot_run is not None
            snapshot_count = (
                snapshot_run["epoch_count"]
                if snapshot_run["status"] in {"running", "stopping"}
                else None
            )
            batches = manager().history_batches(run_id, snapshot_count)
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "schema": "gnss-stream/1",
                    "run": snapshot_run,
                    "epochs": next(batches, []),
                    "seq": last_seq,
                    "transport": manager().transport.get(run_id, ""),
                    "position_stale": manager().position_stale.get(run_id, False),
                }
            )
            for batch in batches:
                await websocket.send_json(
                    {"type": "snapshot_page", "schema": "gnss-stream/1", "epochs": batch}
                )
            heartbeat = 0
            while True:
                event_log = list(manager().events.get(run_id, []))
                # Keep status and this event batch in one event-loop turn. A socket
                # send yields, allowing the pump to append final epochs and finish.
                # Reading a newer terminal status afterward would skip that tail.
                info = manager().get(run_id)
                if event_log and event_log[0]["seq"] > last_seq + 1:
                    await websocket.send_json(
                        {"type": "resync_required", "schema": "gnss-stream/1"}
                    )
                    return
                for event in event_log:
                    if event["seq"] > last_seq:
                        await websocket.send_text(
                            json.dumps(event, ensure_ascii=False, allow_nan=False)
                        )
                        last_seq = event["seq"]
                if info and info["status"] not in {"running", "stopping"}:
                    await websocket.send_json(
                        {"type": "run_status", "run": info, "schema": "gnss-stream/1"}
                    )
                    await websocket.close(code=1000)
                    return
                heartbeat += 1
                if heartbeat % 20 == 0:
                    await websocket.send_json(
                        {"type": "heartbeat", "run": info, "schema": "gnss-stream/1"}
                    )
                await asyncio.sleep(0.1)
        except (WebSocketDisconnect, RuntimeError):
            return

    dist = PROJECT_ROOT / "web/dist"
    if dist.is_dir():
        application.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return application


app = create_app()
