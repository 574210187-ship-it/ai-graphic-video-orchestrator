from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from ..events import atomic_json
from ..errors import ProviderError
from .base import RecordProvider


class FixtureProvider(RecordProvider):
    def __init__(self, fixture_file: Path):
        self.path = fixture_file
        if not self.path.is_file():
            raise ProviderError("FIXTURE_NOT_FOUND", str(self.path))

    def _load(self) -> dict:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("records"), list):
            raise ProviderError("FIXTURE_INVALID", str(self.path))
        return value

    def _save(self, value: dict) -> None:
        atomic_json(self.path, value)

    def list_records(self) -> Iterable[dict[str, Any]]:
        return list(self._load()["records"])

    def get_record(self, record_id: str) -> dict[str, Any]:
        for record in self._load()["records"]:
            if str(record.get("record_id") or record.get("id")) == record_id:
                return record
        raise ProviderError("RECORD_NOT_FOUND", record_id)

    def download_attachment(self, file_token: str, target: Path) -> dict[str, Any]:
        files = self._load().get("files") or {}
        source = files.get(file_token)
        if not source:
            raise ProviderError("FIXTURE_FILE_TOKEN_NOT_FOUND", file_token)
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = self.path.parent / source_path
        if not source_path.is_file():
            raise ProviderError("FIXTURE_SOURCE_NOT_FOUND", str(source_path))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        return {"ok": True, "bytes": target.stat().st_size, "output": str(target)}

    def attach_files(
        self,
        record_id: str,
        field_name: str,
        paths: list[Path],
        *,
        replace_same_name: bool = False,
    ) -> dict[str, Any]:
        value = self._load()
        record = next((item for item in value["records"] if item.get("record_id") == record_id), None)
        if record is None:
            raise ProviderError("RECORD_NOT_FOUND", record_id)
        fields = record.setdefault("fields", {})
        existing = [item for item in fields.get(field_name, []) if isinstance(item, dict)]
        names = {path.name for path in paths}
        if replace_same_name:
            existing = [item for item in existing if item.get("name") not in names]
        added = []
        for index, path in enumerate(paths, 1):
            item = {
                "name": path.name,
                "size": path.stat().st_size,
                "file_token": f"fixture-{record_id}-{index}-{path.stat().st_size}",
            }
            existing.append(item)
            added.append(item)
        fields[field_name] = existing
        self._save(value)
        return {"ok": True, "record_id": record_id, "added": added, "attachments": existing}

    def update_fields(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        value = self._load()
        record = next((item for item in value["records"] if item.get("record_id") == record_id), None)
        if record is None:
            raise ProviderError("RECORD_NOT_FOUND", record_id)
        record.setdefault("fields", {}).update(fields)
        self._save(value)
        actual = self.get_record(record_id).get("fields") or {}
        mismatches = {key: {"expected": expected, "actual": actual.get(key)} for key, expected in fields.items() if actual.get(key) != expected}
        return {"ok": not mismatches, "verify": {"ok": not mismatches, "mismatches": mismatches}}
