"""Batch failures must not lose completed epochs or leave stale success metrics."""

import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from gnss_workbench.cli import app
from gnss_workbench.settings import COURSE_ROOT


def test_cli_preserves_partial_results_on_broken_input(tmp_path: Path) -> None:
    lines = (COURSE_ROOT / "data/D02_sim_clean.jsonl").read_text(encoding="utf-8").splitlines()
    source = tmp_path / "broken.jsonl"
    source.write_text("\n".join([lines[0], lines[1], lines[2], "{invalid-json"]), encoding="utf-8")
    out = tmp_path / "results"
    result = CliRunner().invoke(app, ["solve", "--input", str(source), "--out", str(out)])
    assert result.exit_code == 1
    assert "Preserved 2 epochs" in result.output
    for name in ["baseline.csv", "improved.csv"]:
        with (out / name).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert [row["epoch_id"] for row in rows] == ["0", "1"]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["epochs"] == 2
    assert "JSONDecodeError" in manifest["error"]
    assert len((out / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    assert not (out / "metrics.json").exists()


def test_cli_refuses_to_overwrite_previous_evidence(tmp_path: Path) -> None:
    out = tmp_path / "previous"
    out.mkdir()
    evidence = out / "metrics.json"
    evidence.write_text('{"original": true}', encoding="utf-8")
    result = CliRunner().invoke(
        app,
        ["solve", "--input", str(COURSE_ROOT / "data/D01_real_excerpt.jsonl"), "--out", str(out)],
    )
    assert result.exit_code != 0
    assert "must be empty" in result.output
    assert evidence.read_text(encoding="utf-8") == '{"original": true}'
    assert list(out.iterdir()) == [evidence]
