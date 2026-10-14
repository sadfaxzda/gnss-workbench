"""The same solver as the web service, usable without a browser or server."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .core.models import SolverConfig
from .core.solver import PositioningEngine
from .evaluation import evaluate_run
from .io import export_solutions, navigation_from, read_epochs
from .settings import COURSE_ROOT

app = typer.Typer(no_args_is_help=True)


@app.command()
def solve(
    input: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option()],
    navigation: Annotated[Path, typer.Option(exists=True)] = COURSE_ROOT
    / "data"
    / "navigation.json",
    truth: Annotated[Path | None, typer.Option(exists=True)] = None,
    disable_fde: bool = False,
) -> None:
    """Solve a JSONL stream, save both solutions and complete diagnosis evidence."""
    config = SolverConfig(enable_fde=not disable_fde)
    engine = PositioningEngine(navigation_from(navigation), config)
    baseline, improved = [], []
    out.mkdir(parents=True, exist_ok=True)
    with (out / "diagnostics.jsonl").open("w", encoding="utf-8") as stream:
        for epoch in read_epochs(input):
            b, i = engine.solve(epoch)
            baseline.append(b)
            improved.append(i)
            stream.write(
                json.dumps(
                    {"baseline": b.to_dict(), "improved": i.to_dict()},
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )
    export_solutions(out / "baseline.csv", baseline)
    export_solutions(out / "improved.csv", improved)
    manifest = {
        "schema": "gnss-run/1",
        "version": __version__,
        "input": input.name,
        "input_sha256": hashlib.sha256(input.read_bytes()).hexdigest(),
        "navigation_sha256": hashlib.sha256(navigation.read_bytes()).hexdigest(),
        "configuration": asdict(config),
        "epochs": len(baseline),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if truth:
        metrics = evaluate_run(input, truth, out)
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        typer.echo(json.dumps(metrics, indent=2))
    typer.echo(f"Solved {len(baseline)} epochs → {out}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the local application (one API owner for its supervised workers)."""
    import uvicorn

    uvicorn.run("gnss_workbench.api:app", host=host, port=port)


if __name__ == "__main__":
    app()
