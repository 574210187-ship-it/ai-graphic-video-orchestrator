from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import resolve_path
from .errors import ContractError
from .models import Attachment, Candidate
from .providers import FixtureProvider, RecordProvider


def make_provider(config: dict) -> RecordProvider:
    kind = config["provider"].get("type")
    if kind == "fixture":
        return FixtureProvider(resolve_path(config, config["provider"]["fixture_file"]))
    if kind == "feishu":
        from .providers.feishu import FeishuProvider

        return FeishuProvider(config)
    raise ContractError("PROVIDER_UNSUPPORTED", str(kind))


def _attachment_items(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def is_video_attachment(item: dict, extensions: set[str]) -> bool:
    name = str(item.get("name") or item.get("file_name") or "").lower()
    mime = str(item.get("mime_type") or item.get("type") or "").lower()
    return Path(name).suffix.lower() in extensions or mime.startswith("video/")


def field_has_video(fields: dict, field_name: str, extensions: set[str]) -> bool:
    return any(is_video_attachment(item, extensions) for item in _attachment_items(fields.get(field_name)))


def _classification_matches(value: Any, expected: str) -> bool:
    if isinstance(value, list):
        return any(_classification_matches(item, expected) for item in value)
    if isinstance(value, dict):
        return any(_classification_matches(value.get(key), expected) for key in ("text", "name", "value", "id"))
    return str(value or "") == expected


def candidate_from_record(record: dict, config: dict) -> Candidate | None:
    record_id = str(record.get("record_id") or record.get("id") or "")
    if not record_id or record_id in {str(item) for item in config["queue"].get("denylist", [])}:
        return None
    fields = record.get("fields") or {}
    mapping = config["fields"]
    if not _classification_matches(fields.get(mapping["classification"]), str(mapping["classification_value"])):
        return None
    extensions = {str(item).lower() for item in config["queue"].get("video_extensions", [])}
    if field_has_video(fields, mapping["product"], extensions) or field_has_video(fields, mapping["published"], extensions):
        return None

    source_field = ""
    source_items: list[dict] = []
    for name in mapping["source_priority"]:
        items = [item for item in _attachment_items(fields.get(name)) if Attachment.from_raw(item).file_token]
        if items:
            source_field, source_items = name, items
            break
    if not source_items:
        return None
    if len(source_items) != 1:
        raise ContractError("SOURCE_NOT_UNIQUE", record_id, detail={"field": source_field, "count": len(source_items)})
    title = str(fields.get(mapping.get("title", "")) or "") if mapping.get("title") else ""
    return Candidate(record_id=record_id, source_field=source_field, source=Attachment.from_raw(source_items[0]), title=title, fields=fields)


def discover_candidates(provider: RecordProvider, config: dict) -> tuple[list[Candidate], list[dict]]:
    candidates: list[Candidate] = []
    blocked: list[dict] = []
    for record in provider.list_records():
        try:
            candidate = candidate_from_record(record, config)
        except ContractError as exc:
            blocked.append({"record_id": record.get("record_id") or record.get("id"), **exc.as_dict()})
            continue
        if candidate is not None:
            candidates.append(candidate)
    return candidates, blocked
