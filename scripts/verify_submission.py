"""Verify an extracted submission using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def verify(root: Path) -> dict:
    root = root.resolve()
    manifest = json.loads((root / "SHA256SUMS.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("Empty or invalid checksum inventory")
    if not {"SOURCE_MANIFEST.json", "SUBMISSION.txt"} <= manifest.keys():
        raise ValueError("Missing sealed source metadata in checksum inventory")
    for name, expected in manifest.items():
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts or "\\" in name:
            raise ValueError(f"Unsafe inventory path: {name}")
        target = root / pure
        if not target.resolve().is_relative_to(root) or target.is_symlink():
            raise ValueError(f"Entry leaves source directory or is a symlink: {name}")
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Missing or changed file: {name}")
    source = json.loads((root / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    hashes = source["files"]
    if not hashes or any(manifest.get(name) != value for name, value in hashes.items()):
        raise ValueError("Source inventory does not match archive inventory")
    canonical = json.dumps(
        hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != source["content_sha256"]:
        raise ValueError("Source inventory identity mismatch")
    identity = source["source_identity"]
    if not re.fullmatch(r"[0-9a-f]{40}|snapshot-sha256:[0-9a-f]{64}", identity):
        raise ValueError("Invalid source identity")
    if identity.startswith("snapshot-sha256:") and identity != f"snapshot-sha256:{digest}":
        raise ValueError("Snapshot source identity mismatch")
    revision = re.search(
        r"^Source revision: (.+)$",
        (root / "SUBMISSION.txt").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if revision is None or revision.group(1) != identity:
        raise ValueError("Submission source identity does not match source manifest")
    # Generated local runtime, caches and virtual environments may be added after
    # extraction; this check verifies every delivered byte, not local run history.
    return dict(files_verified=len(manifest), source_files=len(hashes), source_identity=identity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))


if __name__ == "__main__":
    main()
