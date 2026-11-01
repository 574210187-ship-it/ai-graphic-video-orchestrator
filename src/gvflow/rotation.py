from __future__ import annotations

import json
from pathlib import Path

from .business import load_business_profile
from .events import atomic_json, file_lease, now_iso
from .errors import ContractError


def _runs_dir(config: dict) -> Path:
    path = Path(config["project"]["runs_dir"])
    if not path.is_absolute():
        path = Path(config["_config_dir"]) / path
    return path.resolve()


def _state_path(config: dict, profile: dict) -> Path:
    configured = (profile.get("assets") or {}).get("rotation_state")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = Path(config["_config_dir"]) / path
        return path.resolve()
    return _runs_dir(config) / "_shared" / "background_rotation.json"


def _load_state(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": 1, "next_index": 1, "pending": None, "last_commit": None}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1:
        raise ContractError("ROTATION_STATE_SCHEMA_INVALID", str(path))
    return value


def reserve_background(config: dict, record_id: str) -> dict:
    _, profile = load_business_profile(config)
    backgrounds = (profile.get("space") or {}).get("backgrounds") or []
    if not backgrounds:
        raise ContractError("BACKGROUND_CATALOG_EMPTY")
    state_path = _state_path(config, profile)
    with file_lease(state_path, actor_id=config["project"]["actor_id"], record_id=record_id):
        state = _load_state(state_path)
        pending = state.get("pending")
        if pending and pending.get("record_id") != record_id:
            raise ContractError("BACKGROUND_ROTATION_PENDING", detail=pending)
        if not pending:
            index = int(state.get("next_index") or 1)
            pending = {"record_id": record_id, "index": index, "reserved_at": now_iso()}
            state["pending"] = pending
            atomic_json(state_path, state)
        index = int(pending["index"])
        if index < 1 or index > len(backgrounds):
            raise ContractError("BACKGROUND_INDEX_INVALID", detail={"index": index, "count": len(backgrounds)})
        result = {"record_id": record_id, "background_index": index, "space_path": backgrounds[index - 1], "state": str(state_path)}
        manifest_path = _runs_dir(config) / record_id / "task_manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["background_reservation"] = result
            atomic_json(manifest_path, manifest)
        return result


def commit_background(config: dict, record_id: str) -> dict:
    _, profile = load_business_profile(config)
    backgrounds = (profile.get("space") or {}).get("backgrounds") or []
    state_path = _state_path(config, profile)
    with file_lease(state_path, actor_id=config["project"]["actor_id"], record_id=record_id):
        state = _load_state(state_path)
        pending = state.get("pending")
        if not pending or pending.get("record_id") != record_id:
            raise ContractError("BACKGROUND_COMMIT_WITHOUT_RESERVATION", record_id)
        index = int(pending["index"])
        state["next_index"] = index % len(backgrounds) + 1
        state["last_commit"] = {**pending, "committed_at": now_iso()}
        state["pending"] = None
        atomic_json(state_path, state)
        return state


def abort_background(config: dict, record_id: str) -> dict:
    _, profile = load_business_profile(config)
    state_path = _state_path(config, profile)
    with file_lease(state_path, actor_id=config["project"]["actor_id"], record_id=record_id):
        state = _load_state(state_path)
        pending = state.get("pending")
        if pending and pending.get("record_id") != record_id:
            raise ContractError("BACKGROUND_ROTATION_PENDING", detail=pending)
        state["pending"] = None
        atomic_json(state_path, state)
        return state
