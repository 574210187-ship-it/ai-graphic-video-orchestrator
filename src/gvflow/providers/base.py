from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable


class RecordProvider(ABC):
    @abstractmethod
    def list_records(self) -> Iterable[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_record(self, record_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def download_attachment(self, file_token: str, target: Path) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def attach_files(
        self,
        record_id: str,
        field_name: str,
        paths: list[Path],
        *,
        replace_same_name: bool = False,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_fields(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def doctor(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.__class__.__name__}
