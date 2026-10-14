"""The same solver as the web service, usable without a browser or server."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

import typer

from . import __version__
from .core.models import SolverConfig
from .core.solver import PositioningEngine
from .evaluation import evaluate_run
from .io import export_solutions, navigation_from, read_epochs
from .provenance import source_revision
from .settings import COURSE_ROOT

app = typer.Typer(no_args_is_help=True)


@app.command()
def solve(
    input: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option(file_okay=False)],
    navigation: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = COURSE_ROOT
    / "data"
    / "navigation.json",
    truth: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    disable_fde: bool = False,
    algorithm: Literal["single_fde", "consensus", "adaptive_gnc"] = "consensus",
    noise_sigma_m: float = 1.0,
) -> None:
    """Solve a JSONL stream, save both solutions and complete diagnosis evidence."""
    config = SolverConfig(
        enable_fde=not disable_fde, algorithm=algorithm, noise_sigma_m=noise_sigma_m
    )
    engine = PositioningEngine(navigation_from(navigation), config)
    baseline, improved = [], []
    if out.exists() and any(out.iterdir()):
        raise typer.BadParameter("Output directory must be empty; choose a new --out path")
    out.mkdir(parents=True, exist_ok=True)
    failure: str | None = None
    try:
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
    except (ValueError, KeyError, TypeError, OSError) as error:
        failure = f"{type(error).__name__}: {error}"
    export_solutions(out / "baseline.csv", baseline)
    export_solutions(out / "improved.csv", improved)
    manifest = {
        "schema": "gnss-run/1",
        "version": __version__,
        "git_revision": source_revision(),
        "input": input.name,
        "input_sha256": hashlib.sha256(input.read_bytes()).hexdigest(),
        "navigation_sha256": hashlib.sha256(navigation.read_bytes()).hexdigest(),
        "configuration": asdict(config),
        "epochs": len(baseline),
        "status": "failed" if failure else "completed",
        "error": failure,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if failure:
        typer.echo(f"Stopped: {failure}. Preserved {len(baseline)} epochs → {out}", err=True)
        raise typer.Exit(1)
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


@app.command()
def benchmark(
    out: Annotated[Path, typer.Option()], seed: int = 20261016, samples: int = 84
) -> None:
    """Run seven reproducible stress families against four algorithm configurations."""
    from .benchmark import run_benchmark

    run_benchmark(out, seed, samples)
    typer.echo(f"Benchmark complete → {out / 'report.md'}")


@app.command("cross-check")
def cross_check_command(
    out: Annotated[Path, typer.Option()] = Path("runtime/cross-check.json"),
) -> None:
    """Check snapshot WLS with the optional Stanford gnss_lib_py tool."""
    from .research_tools import cross_check

    result = cross_check(out)
    typer.echo(
        f"{result['epochs']} snapshots checked; max state delta {result['max_state_difference_m']:.6g} m"
    )


if __name__ == "__main__":
    app()
