from __future__ import annotations

import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .artifacts import sha256_file
from .events import append_event, atomic_json
from .models import Candidate
from .providers.base import RecordProvider


def run_id(record_id: str) -> str:
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    return f"gv-{stamp}-{record_id}-{uuid.uuid4().hex[:8]}"


def _source_suffix(name: str) -> str:
    suffix = Path(name).suffix
    return suffix if suffix else ".bin"


def prepare_manifest(provider: RecordProvider, candidate: Candidate, config: dict) -> tuple[Path, dict]:
    runs_dir = Path(config["project"]["runs_dir"])
    if not runs_dir.is_absolute():
        runs_dir = (Path(config["_config_dir"]) / runs_dir).resolve()
    row_dir = runs_dir / candidate.record_id
    row_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = row_dir / "task_manifest.json"
    existing = None
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = provider.get_record(candidate.record_id)
    source_target = row_dir / f"source{_source_suffix(candidate.source.name)}"
    provider.download_attachment(candidate.source.file_token, source_target)
    source_hash = sha256_file(source_target)
    if existing and existing.get("source", {}).get("file_token") == candidate.source.file_token and existing.get("source", {}).get("sha256") == source_hash:
        return manifest_path, existing
    rid = run_id(candidate.record_id)
    manifest = {
        "schema_version": 1,
        "run_id": rid,
        "record_id": candidate.record_id,
        "actor_id": config["project"]["actor_id"],
        "engine": config["engine"]["name"],
        "state": "SOURCE_DOWNLOADED",
        "selection": {
            "priority": candidate.selection_priority,
            "reason": candidate.selection_reason,
        },
        "source": {
            **candidate.source.to_dict(),
            "source_field": candidate.source_field,
            "local_path": str(source_target.resolve()),
            "sha256": source_hash,
            "detected_mime": mimetypes.guess_type(candidate.source.name)[0],
        },
        "row_snapshot": current,
        "route": None,
        "controller_result": str((row_dir / "controller_result.json").resolve()),
        "events": str((row_dir / "events.jsonl").resolve()),
        "attempts": 0,
    }
    atomic_json(manifest_path, manifest)
    append_event(
        row_dir / "events.jsonl",
        run_id=rid,
        record_id=candidate.record_id,
        actor_id=config["project"]["actor_id"],
        state="SOURCE_DOWNLOADED",
        selection_priority=candidate.selection_priority,
        selection_reason=candidate.selection_reason,
        source_file_token=candidate.source.file_token,
        source_sha256=source_hash,
    )
    return manifest_path, manifest


def update_manifest(path: Path, **changes: object) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    value.update(changes)
    atomic_json(path, value)
    return value
