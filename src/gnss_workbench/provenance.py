"""Identify both Git checkouts and sealed source distributions."""

import re
import subprocess
from pathlib import Path

from .settings import PROJECT_ROOT


def source_revision(root: Path = PROJECT_ROOT) -> str:
    if (root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
            )
            revision = result.stdout.strip()
            if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", revision):
                return revision
        except OSError:
            pass
    submission = root / "SUBMISSION.txt"
    if submission.is_file():
        match = re.search(
            r"^Source revision: ([0-9a-f]{40})$",
            submission.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            return match.group(1)
    return "uncommitted"
