"""Verify the original ZIP content, including its documented manifest discrepancy."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "fixtures/course"
manifest = json.loads((root / "MANIFEST_SHA256.json").read_text(encoding="utf-8"))["files"]
# This is the actual unmodified member from the user-supplied ZIP; see docs/validation.md.
manifest["docs/作业任务书.docx"] = (
    "7aa7b3330e4c33ad62786cb9c53a114cce98d77d2bbb9318d555aff7ed196a28"
)
for name, expected in manifest.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Fixture changed: {name}")
print(f"Verified {len(manifest)} original package files (known docx manifest discrepancy pinned)")
