import json
import time

from fastapi.testclient import TestClient

from gnss_workbench.api import create_app


def wait_completed(client, run_id):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = client.get(f"/api/runs/{run_id}").json()
        if result["status"] not in {"running", "stopping"}:
            return result
        time.sleep(0.05)
    raise AssertionError("Worker did not finish")


def test_file_run_websocket_export_and_restart(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert len(client.get("/api/datasets").json()) == 3
        response = client.post("/api/runs", json={"interval_seconds": 0})
        assert response.status_code == 201
        run_id = response.json()["id"]
        with client.websocket_connect(f"/api/runs/{run_id}/stream") as ws:
            seen = set()
            for _ in range(1000):
                message = ws.receive_json()
                assert message["schema"] == "gnss-stream/1"
                if message["type"] == "snapshot":
                    seen.update(e["epoch_id"] for e in message["epochs"])
                if message["type"] == "epoch":
                    seen.add(message["epoch_id"])
                if message["type"] == "run_status":
                    break
            assert len(seen) == 600
        run = wait_completed(client, run_id)
        assert run["status"] == "completed", run
        assert run["summary"]["evaluation"]["improved"]["h_p95_m"] < 5
        history = client.get(f"/api/runs/{run_id}/epochs").json()
        assert len(history) == 600
        assert history[460]["improved"]["x_m"] is None
        download = client.get(f"/api/runs/{run_id}/download/improved.csv")
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/octet-stream"
        assert download.headers["content-disposition"].startswith("attachment;")
        manifest = client.get(f"/api/runs/{run_id}/download/manifest.json").json()
        assert len(manifest["input_sha256"]) == 64
        assert manifest["reference_truth_used_for_positioning"] is False
        assert client.get("/api/runs/unknown").status_code == 404
    with TestClient(create_app(tmp_path)) as restarted:
        assert restarted.get(f"/api/runs/{run_id}").json()["status"] == "completed"
        assert len(restarted.get(f"/api/runs/{run_id}/epochs").json()) == 600


def test_scenario_and_ablation_are_recorded(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/api/runs",
            json={
                "dataset_id": "D02_sim_clean",
                "interval_seconds": 0,
                "scenario": {
                    "kind": "satellite_bias",
                    "start_epoch": 40,
                    "duration": 25,
                    "sat_id": "G20",
                    "bias_m": -95,
                },
            },
        )
        run_id = response.json()["id"]
        run = wait_completed(client, run_id)
        assert run["status"] == "completed", run
        assert run["summary"]["evaluation"]["improved"]["fault_detection_recall"] >= 0.9
        source = client.get(f"/api/runs/{run_id}/download/input.jsonl").text
        assert len(source.splitlines()) == 600
        assert json.loads(source.splitlines()[40])["epoch_id"] == 40
        assert (
            client.post(
                "/api/runs", json={"source": "tcp", "scenario": {"kind": "satellite_bias"}}
            ).status_code
            == 422
        )


def test_active_run_exclusive_and_stop(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        run_id = client.post("/api/runs", json={"interval_seconds": 1}).json()["id"]
        assert client.post("/api/runs", json={}).status_code == 409
        assert client.get(f"/api/runs/{run_id}/download/improved.csv").status_code == 409
        assert client.post(f"/api/runs/{run_id}/stop").status_code == 200
        assert wait_completed(client, run_id)["status"] == "stopped"


def test_stream_rejects_foreign_origin(tmp_path):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with TestClient(create_app(tmp_path)) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/api/runs/unknown/stream", headers={"origin": "https://example.org"}
            ):
                pass
