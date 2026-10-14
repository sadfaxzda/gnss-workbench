"""Immutable imported inputs; server-generated IDs never expose arbitrary paths."""

import hashlib
import json
import tempfile
import uuid
from pathlib import Path

from .contracts import DatasetImport
from .io import navigation_from, read_epochs, validate_navigation
from .settings import COURSE_ROOT, DATASETS


class DatasetStore:
    def __init__(self, root: Path):
        self.root = root / "datasets"
        self.root.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict]:
        builtins = [{"id": key, **value} for key, value in DATASETS.items()]
        return builtins + [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("custom_*/info.json"))
        ]

    def resolve(self, dataset_id: str) -> tuple[Path, Path]:
        if dataset_id in DATASETS:
            return (
                COURSE_ROOT / "data" / f"{dataset_id}.jsonl",
                COURSE_ROOT / "data/navigation.json",
            )
        if not dataset_id.startswith("custom_") or not dataset_id.removeprefix("custom_").isalnum():
            raise ValueError("Unknown dataset")
        directory = self.root / dataset_id
        if not (directory / "info.json").is_file():
            raise ValueError("Unknown dataset")
        return directory / "input.jsonl", directory / "navigation.json"

    def create(self, request: DatasetImport) -> dict:
        dataset_id = "custom_" + uuid.uuid4().hex
        nav = (
            validate_navigation(request.navigation)
            if request.navigation is not None
            else navigation_from(COURSE_ROOT / "data/navigation.json")
        )
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            stage = Path(temporary) / "payload"
            stage.mkdir()
            source = stage / "input.jsonl"
            source.write_text(request.jsonl, encoding="utf-8")
            count = 0
            invalid = 0
            for epoch in read_epochs(source):
                count += 1
                invalid += bool(epoch.data_error)
                if count > 5000:
                    raise ValueError("网页导入上限为 5000 历元；更长文件请用 gnss solve")
            if not count:
                raise ValueError("文件中没有 epoch 观测帧")
            info = {
                "id": dataset_id,
                "title": request.name,
                "kind": "imported",
                "epochs": count,
                "description": f"本地导入 · {count} 历元 · {invalid} 个观测异常历元 · 未提供独立真值",
            }
            (stage / "navigation.json").write_text(json.dumps(nav), encoding="utf-8")
            (stage / "info.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
            (stage / "hashes.json").write_text(
                json.dumps({"input_sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
            )
            stage.rename(self.root / dataset_id)
        return info
