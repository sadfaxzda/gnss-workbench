"""Create a verifiable hand-in archive from Git or an explicit source snapshot.

Run after `pnpm --dir web build`. Excludes local runtime, credentials, Git history,
virtual environments and node_modules by taking source from Git's tracked inventory.
Use --source-snapshot for a downloaded source folder without Git metadata. Its
allowlisted source inventory is identified by SHA256, never a fabricated commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREES = (
    "src",
    "scripts",
    "tests",
    "docs",
    "fixtures/course",
    "migrations",
    "web/src",
    "web/e2e",
    ".github/workflows",
)
SOURCE_FILES = (
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "DESIGN.md",
    "PRODUCT.md",
    "pyproject.toml",
    "uv.lock",
    "alembic.ini",
    ".python-version",
    ".node-version",
    ".gitignore",
    ".gitattributes",
    "web/package.json",
    "web/pnpm-lock.yaml",
    "web/pnpm-workspace.yaml",
    "web/index.html",
    "web/ports.ts",
    "web/vite.config.ts",
    "web/vitest.config.ts",
    "web/playwright.config.ts",
    "web/eslint.config.js",
    "web/tsconfig.json",
    "web/tsconfig.app.json",
    "web/tsconfig.node.json",
    "web/.prettierrc.json",
    "web/.prettierignore",
)


def snapshot_inventory(root: Path) -> dict[str, bytes]:
    """Include documented project material, not runtime or arbitrary root files."""
    files = {}
    for relative in SOURCE_TREES:
        tree = root / relative
        if tree.is_symlink():
            raise ValueError(f"Source tree must not be a symlink: {relative}")
        for path in sorted(tree.rglob("*")):
            name = path.relative_to(root).as_posix()
            parts = path.relative_to(tree).parts
            if any(
                part.startswith(".") or part in {"__pycache__", "node_modules", "runtime"}
                for part in parts
            ):
                continue
            if path.is_symlink():
                raise ValueError(f"Source entry must not be a symlink: {name}")
            if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
                files[name] = path.read_bytes()
    for name in SOURCE_FILES:
        path = root / name
        if path.is_symlink():
            raise ValueError(f"Source entry must not be a symlink: {name}")
        if path.is_file():
            files[name] = path.read_bytes()
    for required in (
        "pyproject.toml",
        "uv.lock",
        "src/gnss_workbench/cli.py",
        "fixtures/course/data/navigation.json",
        "web/package.json",
        "web/pnpm-lock.yaml",
    ):
        if required not in files:
            raise ValueError(f"Required submission source missing: {required}")
    return files


def inventory_identity(files: dict[str, bytes]) -> tuple[str, dict[str, str]]:
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    canonical = json.dumps(
        hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest(), hashes


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def build_archive(destination: Path, *, source_snapshot: bool = False) -> None:
    if not source_snapshot and not (ROOT / ".git").exists():
        raise SystemExit(
            "No Git metadata. Use --source-snapshot to seal the actual source with SHA256."
        )
    if not source_snapshot and git("status", "--porcelain"):
        raise SystemExit(
            "Commit the reviewed changes first; the submission must identify exact source."
        )
    dist = ROOT / "web/dist"
    if dist.is_symlink():
        raise SystemExit("Built frontend directory must not be a symlink")
    if not (dist / "index.html").is_file():
        raise SystemExit("Build the frontend first: pnpm --dir web build")
    if destination.exists():
        raise SystemExit("Archive already exists; choose a new --out path.")
    files: dict[str, bytes] = snapshot_inventory(ROOT) if source_snapshot else {}
    if not source_snapshot:
        for name in git("ls-files", "-z").split("\0"):
            path = ROOT / name
            if path.is_symlink():
                raise SystemExit(f"Source entry must not be a symlink: {name}")
            if path.is_file():
                files[name] = path.read_bytes()
    for path in dist.rglob("*"):
        if path.is_file():
            if path.is_symlink():
                raise SystemExit(f"Built asset must not be a symlink: {path}")
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()

    source_digest, source_hashes = inventory_identity(files)
    revision = f"snapshot-sha256:{source_digest}" if source_snapshot else git("rev-parse", "HEAD")
    files["SOURCE_MANIFEST.json"] = (
        json.dumps(
            dict(
                source_identity=revision,
                content_sha256=source_digest,
                files=source_hashes,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode()
    files["SUBMISSION.txt"] = (
        "GNSS Workbench course submission candidate\n"
        f"Source revision: {revision}\n\n"
        "1. Read README.md and docs/demo-guide.md.\n"
        "2. Install uv, then run: uv sync --locked\n"
        "3. Run: uv run gnss serve; open http://127.0.0.1:8000\n"
        "The built frontend is included; Node is only needed for frontend development.\n"
        "First-time dependency installation requires network access.\n"
        "4. Fresh batch results and ablation are in submission-results/.\n"
        "5. Run: python scripts/verify_submission.py --root .\n\n"
        "The report remains a draft until actual members fill and verify their contributions.\n"
        "Hidden teacher cases and the oral defense are not claimed as passed.\n"
        "This archive includes course material: share within the authorized course scope.\n"
    ).encode()

    with tempfile.TemporaryDirectory(prefix="gnss-hand-in-") as temporary:
        # Run the captured bytes, not a live checkout which might change during packaging.
        stage = Path(temporary) / "source"
        for name, data in files.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        environment = {
            **os.environ,
            "PYTHONPATH": str(stage / "src"),
            "GNSS_COURSE_ROOT": str(stage / "fixtures/course"),
        }
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
                str(stage / "fixtures/course/data" / f"{dataset}.jsonl"),
                "--out",
                str(output),
            ]
            truth = stage / "fixtures/course/reference" / f"{dataset}_truth.csv"
            if truth.is_file():
                command.extend(["--truth", str(truth)])
            if disabled:
                command.append("--disable-fde")
            subprocess.run(
                command, cwd=stage, env=environment, check=True, capture_output=True, text=True
            )
            for path in output.iterdir():
                files[f"submission-results/{name}/{path.name}"] = path.read_bytes()
            print(f"Prepared {name}", flush=True)

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
    parser.add_argument("--source-snapshot", action="store_true")
    args = parser.parse_args()
    build_archive(args.out.resolve(), source_snapshot=args.source_snapshot)
