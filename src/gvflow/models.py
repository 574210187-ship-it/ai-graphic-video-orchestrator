from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Attachment:
    name: str
    file_token: str
    size: int | None = None
    mime_type: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "Attachment":
        return cls(
            name=str(raw.get("name") or raw.get("file_name") or "attachment"),
            file_token=str(raw.get("file_token") or raw.get("attachmentToken") or raw.get("id") or ""),
            size=int(raw["size"]) if raw.get("size") is not None else None,
            mime_type=raw.get("mime_type") or raw.get("type"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    record_id: str
    source_field: str
    source: Attachment
    title: str = ""
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["source"] = self.source.to_dict()
        return value


@dataclass(frozen=True)
class Artifact:
    branch: str
    path: str
    name: str
    size: int
    sha256: str
    chat_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def file(self) -> Path:
        return Path(self.path)
