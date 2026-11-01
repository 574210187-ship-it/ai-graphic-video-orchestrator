from __future__ import annotations

import json
import traceback
from pathlib import Path

from .artifacts import load_and_validate_controller_result
from .controllers import execute_controller
from .errors import ContractError, GvflowError
from .events import append_event, atomic_json, file_lease, now_iso
from .manifest import prepare_manifest, update_manifest
from .queue import candidate_from_record, discover_candidates, is_video_attachment, make_provider


def _runs_dir(config: dict) -> Path:
    path = Path(config["project"]["runs_dir"])
    if not path.is_absolute():
        path = Path(config["_config_dir"]) / path
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def discover(config: dict) -> dict:
    provider = make_provider(config)
    candidates, blocked = discover_candidates(provider, config)
    return {"ok": True, "count": len(candidates), "rows": [item.to_dict() for item in candidates], "blocked": blocked}


def prepare(config: dict, record_id: str) -> dict:
    provider = make_provider(config)
    record = provider.get_record(record_id)
    candidate = candidate_from_record(record, config)
    if candidate is None:
        raise ContractError("RECORD_NOT_CURRENTLY_ELIGIBLE", record_id)
    manifest_path, manifest = prepare_manifest(provider, candidate, config)
    return {"ok": True, "manifest": str(manifest_path), "record_id": record_id, "run_id": manifest["run_id"]}


def execute(config: dict, record_id: str) -> dict:
    manifest_path = _runs_dir(config) / record_id / "task_manifest.json"
    if not manifest_path.is_file():
        raise ContractError("TASK_MANIFEST_MISSING", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    attempts = int(manifest.get("attempts") or 0) + 1
    update_manifest(manifest_path, state="EXECUTING", attempts=attempts)
    append_event(
        Path(manifest["events"]),
        run_id=manifest["run_id"],
        record_id=record_id,
        actor_id=config["project"]["actor_id"],
        state="EXECUTING",
        attempt=attempts,
        engine=config["engine"]["name"],
    )
    result_path = execute_controller(manifest_path, config)
    result, artifacts = load_and_validate_controller_result(
        result_path,
        minimum_bytes=int(config.get("artifacts", {}).get("minimum_mp4_bytes") or 200_000),
    )
    update_manifest(manifest_path, state="ARTIFACTS_READY", route=result["route"], artifacts=[item.to_dict() for item in artifacts])
    append_event(
        Path(manifest["events"]),
        run_id=manifest["run_id"],
        record_id=record_id,
        actor_id=config["project"]["actor_id"],
        state="ARTIFACTS_READY",
        route=result["route"],
        artifacts=[item.to_dict() for item in artifacts],
    )
    return {"ok": True, "record_id": record_id, "route": result["route"], "artifacts": [item.to_dict() for item in artifacts]}


def record_controller_result(
    config: dict,
    record_id: str,
    *,
    route: str,
    artifact_specs: list[str],
    chat_specs: list[str] | None = None,
) -> dict:
    manifest_path = _runs_dir(config) / record_id / "task_manifest.json"
    if not manifest_path.is_file():
        raise ContractError("TASK_MANIFEST_MISSING", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("route") and manifest["route"] != route:
        raise ContractError("CONTROLLER_ROUTE_MISMATCH", detail={"manifest": manifest["route"], "submitted": route})
    chat_urls = {}
    for spec in chat_specs or []:
        branch, url = spec.split(":", 1)
        chat_urls[branch] = url
    artifacts = []
    for spec in artifact_specs:
        branch, value = spec.split(":", 1)
        path = Path(value).expanduser().resolve()
        artifacts.append({"branch": branch, "path": str(path), "chat_url": chat_urls.get(branch)})
    result = {
        "ok": True,
        "engine": config["engine"]["name"],
        "record_id": record_id,
        "route": route,
        "artifacts": artifacts,
        "errors": [],
    }
    target = Path(manifest["controller_result"])
    atomic_json(target, result)
    _, validated = load_and_validate_controller_result(
        target,
        minimum_bytes=int(config.get("artifacts", {}).get("minimum_mp4_bytes") or 200_000),
    )
    update_manifest(manifest_path, state="ARTIFACTS_READY", route=route, artifacts=[item.to_dict() for item in validated])
    append_event(
        Path(manifest["events"]),
        run_id=manifest["run_id"],
        record_id=record_id,
        actor_id=config["project"]["actor_id"],
        state="ARTIFACTS_READY",
        route=route,
        artifacts=[item.to_dict() for item in validated],
    )
    return {"ok": True, "record_id": record_id, "route": route, "artifacts": [item.to_dict() for item in validated]}


def _recoverable_writeback_state(current: dict, manifest: dict, artifacts: list, config: dict) -> tuple[bool, list[dict]]:
    """Allow retry after a prior attempt uploaded only part of this run's artifacts."""
    fields = current.get("fields") or {}
    mapping = config["fields"]
    source_field = manifest.get("source", {}).get("source_field")
    source_token = manifest.get("source", {}).get("file_token")
    sources = [item for item in (fields.get(source_field) or []) if isinstance(item, dict)] if source_field else []
    if len(sources) != 1 or str(sources[0].get("file_token") or "") != str(source_token or ""):
        return False, []
    extensions = {str(item).lower() for item in config["queue"].get("video_extensions", [])}
    if any(is_video_attachment(item, extensions) for item in (fields.get(mapping["published"]) or []) if isinstance(item, dict)):
        return False, []
    expected = {item.name: item for item in artifacts}
    product_videos = [
        item for item in (fields.get(mapping["product"]) or [])
        if isinstance(item, dict) and is_video_attachment(item, extensions)
    ]
    for item in product_videos:
        match = expected.get(str(item.get("name") or ""))
        if match is None or int(item.get("size") or -1) != match.size or not item.get("file_token"):
            return False, product_videos
    return True, product_videos


def writeback(config: dict, record_id: str) -> dict:
    provider = make_provider(config)
    if config["provider"].get("type") != "fixture" and not config["production"].get("enabled"):
        raise ContractError("PRODUCTION_WRITE_DISABLED")
    manifest_path = _runs_dir(config) / record_id / "task_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_path = Path(manifest["controller_result"])
    result, artifacts = load_and_validate_controller_result(
        result_path,
        minimum_bytes=int(config.get("artifacts", {}).get("minimum_mp4_bytes") or 200_000),
    )
    current = provider.get_record(record_id)
    candidate = candidate_from_record(current, config)
    existing_artifacts: list[dict] = []
    if candidate is None:
        recoverable, existing_artifacts = _recoverable_writeback_state(current, manifest, artifacts, config)
        if not recoverable:
            raise ContractError("RECORD_CHANGED_BEFORE_WRITEBACK", record_id)
    elif candidate.source.file_token != manifest["source"]["file_token"]:
        raise ContractError("SOURCE_CHANGED_BEFORE_WRITEBACK", record_id)
    mapping = config["fields"]
    existing_by_name = {str(item.get("name") or ""): item for item in existing_artifacts}
    missing = [item for item in artifacts if item.name not in existing_by_name]
    if missing:
        attached = provider.attach_files(
            record_id,
            mapping["product"],
            [Path(item.path) for item in missing],
            replace_same_name=bool(config["writeback"].get("replace_same_name")),
        )
        update_manifest(manifest_path, state="WRITTEN", uploaded=attached)
    else:
        attached = {"ok": True, "record_id": record_id, "added": [], "attachments": existing_artifacts, "reused": True}
    previous = (provider.get_record(record_id).get("fields") or {}).get(mapping["execution_log"]) or ""
    line = (
        f"[{now_iso()}] run_id={manifest['run_id']} engine={manifest['engine']} route={result['route']} "
        + " ".join(f"{item.name} bytes={item.size} sha256={item.sha256}" for item in artifacts)
        + " writeback=verified"
    )
    if f"run_id={manifest['run_id']}" in str(previous):
        execution_log = str(previous)
    else:
        execution_log = f"{str(previous).rstrip()}\n{line}".strip()
    fields = {
        mapping["status"]: mapping["completed_status"],
        mapping["note"]: result.get("note") or f"{result['route']}｜已完成并回读",
        mapping["execution_log"]: execution_log,
    }
    provider.update_fields(record_id, fields)
    readback = provider.get_record(record_id)
    actual_fields = readback.get("fields") or {}
    attachments = [item for item in actual_fields.get(mapping["product"], []) if isinstance(item, dict)]
    by_name = {item.get("name"): item for item in attachments}
    mismatches = []
    for item in artifacts:
        actual = by_name.get(item.name)
        if not actual or int(actual.get("size") or -1) != item.size or not actual.get("file_token"):
            mismatches.append({"expected": item.to_dict(), "actual": actual})
    if actual_fields.get(mapping["status"]) != mapping["completed_status"]:
        mismatches.append({"field": mapping["status"], "actual": actual_fields.get(mapping["status"])})
    if f"run_id={manifest['run_id']}" not in str(actual_fields.get(mapping["execution_log"]) or ""):
        mismatches.append({"field": mapping["execution_log"], "error": "line_missing"})
    if mismatches:
        raise ContractError("WRITEBACK_READBACK_MISMATCH", detail=mismatches)
    update_manifest(manifest_path, state="COMPLETED", readback={"verified": True, "attachments": attachments, "fields": fields})
    append_event(
        Path(manifest["events"]),
        run_id=manifest["run_id"],
        record_id=record_id,
        actor_id=config["project"]["actor_id"],
        state="COMPLETED",
        readback_verified=True,
        attachment_tokens=[by_name[item.name].get("file_token") for item in artifacts],
    )
    if result["route"] in {"single_no_lawyer", "multi_no_lawyer"} and manifest.get("background_reservation"):
        from .rotation import commit_background

        commit_background(config, record_id)
    if config["writeback"].get("delete_local_media_after_verified_readback"):
        for item in artifacts:
            try:
                Path(item.path).unlink()
            except FileNotFoundError:
                pass
    return {"ok": True, "record_id": record_id, "route": result["route"], "attachments": attached, "readback_verified": True}


def drain(config: dict, *, limit: int | None = None) -> dict:
    provider = make_provider(config)
    if config["provider"].get("type") != "fixture" and not config["production"].get("enabled"):
        raise ContractError("PRODUCTION_WRITE_DISABLED")
    root = _runs_dir(config)
    actor_id = config["project"]["actor_id"]
    completed: list[str] = []
    failed: list[dict] = []
    with file_lease(root / "single-writer", actor_id=actor_id, record_id="__scope__"):
        candidates, initial_blocked = discover_candidates(provider, config)
        if limit is not None:
            candidates = candidates[:limit]
        for candidate in candidates:
            try:
                current = provider.get_record(candidate.record_id)
                live = candidate_from_record(current, config)
                if live is None:
                    continue
                prepare_manifest(provider, live, config)
                execute(config, candidate.record_id)
                writeback(config, candidate.record_id)
                completed.append(candidate.record_id)
            except Exception as exc:
                if isinstance(exc, GvflowError):
                    error = exc.as_dict()
                else:
                    error = {"ok": False, "error_code": "UNHANDLED_ERROR", "message": str(exc), "traceback": traceback.format_exc(limit=8)}
                error["record_id"] = candidate.record_id
                failed.append(error)
                row_dir = root / candidate.record_id
                row_dir.mkdir(parents=True, exist_ok=True)
                atomic_json(row_dir / "last_error.json", error)
                try:
                    manifest = json.loads((row_dir / "task_manifest.json").read_text(encoding="utf-8"))
                    append_event(
                        Path(manifest["events"]),
                        run_id=manifest["run_id"],
                        record_id=candidate.record_id,
                        actor_id=actor_id,
                        state="FAILED",
                        error_code=error.get("error_code"),
                        summary=error.get("message"),
                        next_action="进入有界恢复；本轮继续下一行",
                        dedupe_key=f"{candidate.record_id}:{error.get('error_code')}",
                    )
                except Exception:
                    pass
                continue
        remaining, final_blocked = discover_candidates(provider, config)
    result = {
        "ok": not remaining,
        "completed": completed,
        "failed": failed,
        "blocked": initial_blocked + final_blocked,
        "remaining": [item.record_id for item in remaining],
        "scope_drained": not remaining,
    }
    atomic_json(root / "drain_result.json", result)
    return result
