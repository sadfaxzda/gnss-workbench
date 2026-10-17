import hashlib
import json
import queue
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient

from gnss_workbench.api import create_app
from gnss_workbench.contracts import RunRequest
from gnss_workbench.io import navigation_from
from gnss_workbench.provenance import source_revision
from gnss_workbench.settings import COURSE_ROOT
from gnss_workbench.worker import run_worker


def test_history_can_reach_records_older_than_one_hundred(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        store = client.app.state.manager.store
        start = datetime(2026, 10, 15, tzinfo=UTC)
        for index in range(105):
            identity = f"{index:032x}"
            store.create(
                identity, (start + timedelta(seconds=index)).isoformat(), RunRequest().model_dump()
            )
            store.update(identity, status="completed")
        first = client.get("/api/runs?offset=0&limit=100")
        last = client.get("/api/runs?offset=100&limit=100")
        assert first.headers["x-total-count"] == last.headers["x-total-count"] == "105"
        items = first.json() + last.json()
        assert len(items) == len({item["id"] for item in items}) == 105
        assert items[-1]["id"] == "0" * 32
        match = client.get("/api/runs", params={"query": f"{8:032x}", "limit": 25})
        assert match.headers["x-total-count"] == "1"
        assert match.json()[0]["id"] == f"{8:032x}"
        assert client.get("/api/runs", params={"query": "%"}).json() == []
        assert client.get("/api/runs?offset=-1").status_code == 422


def test_failed_worker_seals_partial_results_and_manifest(tmp_path, monkeypatch):
    # This test checks manifest propagation, independently of a Git checkout.
    monkeypatch.setattr("gnss_workbench.worker.source_revision", lambda: "a" * 40)
    frame = (
        (COURSE_ROOT / "data/D01_real_excerpt.jsonl").read_text(encoding="utf-8").splitlines()[1]
    )
    source = tmp_path / "broken.jsonl"
    source.write_text(frame + "\n{bad-json\n", encoding="utf-8")
    output = tmp_path / "run"
    events = queue.Queue()
    run_worker(
        "partial",
        RunRequest(dataset_id="D01_real_excerpt", interval_seconds=0).model_dump(),
        str(output),
        events,
        Event(),
        str(source),
    )
    messages = []
    while not events.empty():
        messages.append(events.get_nowait())
    assert messages[-1]["status"] == "failed"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["epoch_count"] == messages[-1]["epoch_count"] == 1
    assert manifest["error"] == messages[-1]["error"]
    assert (
        manifest["input_sha256"]
        == hashlib.sha256((output / "input.jsonl").read_bytes()).hexdigest()
    )
    assert len((output / "improved.csv").read_text(encoding="utf-8").splitlines()) == 2
    assert manifest["git_revision"] == "a" * 40


def test_sealed_distribution_keeps_its_source_revision(tmp_path: Path):
    revision = "b" * 40
    (tmp_path / "SUBMISSION.txt").write_text(
        "GNSS Workbench\nSource revision: " + revision + "\n", encoding="utf-8"
    )
    assert source_revision(tmp_path) == revision
    (tmp_path / "SUBMISSION.txt").write_text("Source revision: unknown\n", encoding="utf-8")
    assert source_revision(tmp_path) == "uncommitted"


def test_long_snapshot_restores_every_epoch_in_acquisition_order(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        manager = client.app.state.manager
        identity = "long-run"
        manager.store.create(identity, datetime.now(UTC).isoformat(), RunRequest().model_dump())
        manager.store.update(identity, status="completed", epoch_count=6001)
        output = tmp_path / "runs" / identity
        output.mkdir(parents=True)
        ids = [*range(6000, -1, -1)]
        (output / "epochs.jsonl").write_text(
            "".join(json.dumps({"type": "epoch", "epoch_id": value}) + "\n" for value in ids),
            encoding="utf-8",
        )
        for status, count in [("completed", 6001), ("interrupted", 6000)]:
            # The last committed count can lag flushed epochs after a hard exit.
            manager.store.update(identity, status=status, epoch_count=count)
            restored = []
            with client.websocket_connect(f"/api/runs/{identity}/stream") as ws:
                while True:
                    event = ws.receive_json()
                    if event["type"] in {"snapshot", "snapshot_page"}:
                        assert len(event["epochs"]) <= 1000
                        restored.extend(row["epoch_id"] for row in event["epochs"])
                    if event["type"] == "run_status":
                        break
            assert restored == ids


def test_import_errors_are_recoverable_and_bom_navigation_is_supported(tmp_path):
    navigation = tmp_path / "navigation.json"
    navigation.write_text(
        "\ufeff" + (COURSE_ROOT / "data/navigation.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert navigation_from(navigation)["schema"] == "GNSS-COURSE-NAV-1.0"
    with TestClient(create_app(tmp_path / "runtime")) as client:
        original = client.get("/api/datasets").json()
        for content in ["", "{bad}", '{"type":"meta"}\n', "[]"]:
            response = client.post("/api/datasets", json={"name": "bad.jsonl", "jsonl": content})
            assert response.status_code == 422
        assert client.get("/api/datasets").json() == original
        content = (COURSE_ROOT / "data/D01_real_excerpt.jsonl").read_text(encoding="utf-8")
        response = client.post(
            "/api/datasets", json={"name": "valid.jsonl", "jsonl": "\ufeff" + content}
        )
        assert response.status_code == 201
        assert response.json()["epochs"] == 20
