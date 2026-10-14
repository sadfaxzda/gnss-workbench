"""Create a private, verifiable hand-in archive from a clean Git checkout.

Run after `pnpm --dir web build`. Excludes local runtime, credentials, Git history,
virtual environments and node_modules by taking source from Git's tracked inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def build_archive(destination: Path) -> None:
    if git("status", "--porcelain"):
        raise SystemExit(
            "Commit the reviewed changes first; the submission must identify exact source."
        )
    dist = ROOT / "web/dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Build the frontend first: pnpm --dir web build")
    if destination.exists():
        raise SystemExit("Archive already exists; choose a new --out path.")
    revision = git("rev-parse", "HEAD")
    tracked = git("ls-files", "-z").split("\0")
    files: dict[str, bytes] = {}
    for name in tracked:
        path = ROOT / name
        if path.is_file():
            files[name] = path.read_bytes()
    for path in dist.rglob("*"):
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()

    with tempfile.TemporaryDirectory(prefix="gnss-hand-in-") as temporary:
        for dataset, disabled in [
            ("D01_real_excerpt", False),
            ("D02_sim_clean", False),
            ("D03_sim_demo", False),
            ("D03_sim_demo", True),
        ]:
            name = dataset + ("_ablation" if disabled else "")
            output = Path(temporary) / name
            command = [
                sys.executable,
                "-m",
                "gnss_workbench.cli",
                "solve",
                "--input",
                str(ROOT / "fixtures/course/data" / f"{dataset}.jsonl"),
                "--out",
                str(output),
            ]
            truth = ROOT / "fixtures/course/reference" / f"{dataset}_truth.csv"
            if truth.is_file():
                command.extend(["--truth", str(truth)])
            if disabled:
                command.append("--disable-fde")
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
            for path in output.iterdir():
                files[f"submission-results/{name}/{path.name}"] = path.read_bytes()
            print(f"Prepared {name}", flush=True)

    files["SUBMISSION.txt"] = (
        "GNSS Workbench course submission candidate\n"
        f"Source revision: {revision}\n\n"
        "1. Read README.md and docs/demo-guide.md.\n"
        "2. Install uv, then run: uv sync --locked\n"
        "3. Run: uv run gnss serve; open http://127.0.0.1:8000\n"
        "The built frontend is included; Node is only needed for frontend development.\n"
        "First-time dependency installation requires network access.\n"
        "4. Fresh batch results and ablation are in submission-results/.\n"
        "5. Verify SHA256SUMS.json before sharing or evaluating this archive.\n\n"
        "The report remains a draft until actual members fill and verify their contributions.\n"
        "Hidden teacher cases and the oral defense are not claimed as passed.\n"
        "This archive includes course material: share within the authorized course scope.\n"
    ).encode()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    files["SHA256SUMS.json"] = (json.dumps(hashes, ensure_ascii=False, indent=2) + "\n").encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(f"gnss-workbench/{name}", data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Archive CRC validation failed")
        for name, expected in hashes.items():
            actual = hashlib.sha256(archive.read(f"gnss-workbench/{name}")).hexdigest()
            if actual != expected:
                raise SystemExit(f"Archive hash mismatch: {name}")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    print(f"Verified {len(hashes)} files; source {revision}\n{destination}\nSHA256 {digest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    build_archive(parser.parse_args().out.resolve())
