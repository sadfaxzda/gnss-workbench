"""Generate contracts from the server; commit generated schemas with source changes."""

import json
from pathlib import Path

from gnss_workbench.api import app

target = Path("web/src/generated/openapi.json")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
