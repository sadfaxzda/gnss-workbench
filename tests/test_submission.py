"""A downloaded source folder must have a verifiable, credential-free hand-in path."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from gnss_workbench.provenance import source_revision


def script(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


packager = script("package_submission")
verifier = script("verify_submission")


def minimal_source(tmp_path):
    for name in [
        "pyproject.toml",
        "uv.lock",
        "src/gnss_workbench/cli.py",
        "fixtures/course/data/navigation.json",
        "web/package.json",
        "web/pnpm-lock.yaml",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source")
    return tmp_path


def test_snapshot_does_not_include_runtime_credentials_or_caches(tmp_path):
    root = minimal_source(tmp_path)
    for name in [
        ".env",
        ".git/config",
        "runtime/private-input.jsonl",
        "web/node_modules/pkg/key",
        "src/gnss_workbench/__pycache__/cli.pyc",
        "docs/.private/token",
    ]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("must not include")
    files = packager.snapshot_inventory(root)
    assert len(files) == 6
    assert all(data == b"source" for data in files.values())
    before, _ = packager.inventory_identity(files)
    (root / "src/gnss_workbench/cli.py").write_text("edited source")
    after, _ = packager.inventory_identity(packager.snapshot_inventory(root))
    assert before != after


def test_snapshot_rejects_symlinked_source(tmp_path):
    root = minimal_source(tmp_path)
    (root / "src/link.py").symlink_to(root / "uv.lock")
    with pytest.raises(ValueError, match="symlink"):
        packager.snapshot_inventory(root)


def test_missing_source_fails_instead_of_producing_incomplete_zip(tmp_path):
    with pytest.raises(ValueError, match="Required submission source missing"):
        packager.snapshot_inventory(tmp_path)


def sealed(tmp_path):
    data = {"src/app.py": b"original source", "uv.lock": b"locked"}
    digest, hashes = packager.inventory_identity(data)
    identity = "snapshot-sha256:" + digest
    for name, content in data.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    source = json.dumps(
        dict(source_identity=identity, content_sha256=digest, files=hashes)
    ).encode()
    (tmp_path / "SOURCE_MANIFEST.json").write_bytes(source)
    (tmp_path / "SUBMISSION.txt").write_text("Source revision: " + identity + "\n")
    hashes = {
        **hashes,
        "SOURCE_MANIFEST.json": hashlib.sha256(source).hexdigest(),
        "SUBMISSION.txt": hashlib.sha256((tmp_path / "SUBMISSION.txt").read_bytes()).hexdigest(),
    }
    (tmp_path / "SHA256SUMS.json").write_text(json.dumps(hashes))
    return identity


def test_sealed_snapshot_identification_and_tamper_detection(tmp_path):
    identity = sealed(tmp_path)
    assert source_revision(tmp_path) == identity
    assert verifier.verify(tmp_path)["source_identity"] == identity
    (tmp_path / "src/app.py").write_text("changed")
    with pytest.raises(ValueError, match="Missing or changed file"):
        verifier.verify(tmp_path)


def test_manifest_cannot_read_outside_extracted_folder(tmp_path):
    sealed(tmp_path)
    manifest = json.loads((tmp_path / "SHA256SUMS.json").read_text())
    manifest["../outside"] = "abc"
    (tmp_path / "SHA256SUMS.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe inventory path"):
        verifier.verify(tmp_path)


def test_metadata_cannot_be_removed_from_checksum_inventory(tmp_path):
    sealed(tmp_path)
    manifest = json.loads((tmp_path / "SHA256SUMS.json").read_text())
    del manifest["SOURCE_MANIFEST.json"]
    (tmp_path / "SHA256SUMS.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Missing sealed source metadata"):
        verifier.verify(tmp_path)
