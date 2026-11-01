from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .errors import ContractError


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        temp = Path(stream.name)
    temp.replace(path)


def append_event(path: Path, *, run_id: str, record_id: str, actor_id: str, state: str, **extra: object) -> dict:
    event = {
        "time": now_iso(),
        "run_id": run_id,
        "record_id": record_id,
        "actor_id": actor_id,
        "state": state,
        **extra,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def file_lease(path: Path, *, actor_id: str, record_id: str, timeout: float = 15.0) -> Iterator[dict]:
    lock = Path(f"{path}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    payload = {"pid": os.getpid(), "actor_id": actor_id, "record_id": record_id, "created_at": now_iso()}
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            os.close(fd)
            break
        except FileExistsError:
            try:
                existing = json.loads(lock.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
            if existing.get("pid") and not _pid_alive(int(existing["pid"])):
                try:
                    lock.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.time() >= deadline:
                raise ContractError("LEASE_CONFLICT", f"锁被占用：{lock}", detail=existing)
            time.sleep(0.2)
    try:
        yield payload
    finally:
        try:
            current = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            current = None
        if current == payload:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
