from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from ..errors import ContractError


def _write_fake_mp4(path: Path, marker: bytes, minimum_size: int = 240_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    payload = (marker + b"-") * ((minimum_size // (len(marker) + 1)) + 1)
    path.write_bytes((header + payload)[:minimum_size])


def _fixture_controller(manifest_path: Path, config: dict) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row_fields = (manifest.get("row_snapshot") or {}).get("fields") or {}
    route = str(row_fields.get("测试路线") or config["engine"].get("fixture_route") or "single_no_lawyer")
    if route in {"single_no_lawyer", "multi_no_lawyer"}:
        branches = ["01", "02"]
    elif route == "single_lawyer":
        branches = ["lawyer"]
    else:
        raise ContractError("FIXTURE_ROUTE_UNSUPPORTED", route)
    row_dir = manifest_path.parent
    artifacts = []
    for branch in branches:
        name = "lawyer_final_animation.mp4" if branch == "lawyer" else f"branch{branch}_final_animation.mp4"
        path = row_dir / name
        _write_fake_mp4(path, f"{manifest['record_id']}:{branch}".encode("utf-8"))
        artifacts.append({"branch": branch, "path": str(path.resolve()), "chat_url": f"fixture://{manifest['record_id']}/{branch}"})
    result = {
        "ok": True,
        "engine": "fixture",
        "record_id": manifest["record_id"],
        "route": route,
        "artifacts": artifacts,
        "errors": [],
    }
    target = Path(manifest["controller_result"])
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def execute_controller(manifest_path: Path, config: dict) -> Path:
    engine = config["engine"]
    if engine.get("name") == "fixture":
        return _fixture_controller(manifest_path, config)
    command = engine.get("command") or []
    if isinstance(command, str):
        command = shlex.split(command)
    if not command:
        raise ContractError("ENGINE_COMMAND_REQUIRED", str(engine.get("name")))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_path = Path(manifest["controller_result"])
    substitutions = {"manifest": str(manifest_path.resolve()), "result": str(result_path.resolve()), "record_id": manifest["record_id"]}
    args = [str(item).format(**substitutions) for item in command]
    proc = subprocess.run(
        args,
        cwd=str(manifest_path.parent),
        capture_output=True,
        text=True,
        timeout=int(engine.get("timeout_seconds") or 3600),
        check=False,
    )
    (manifest_path.parent / "controller.stdout.log").write_text(proc.stdout or "", encoding="utf-8")
    (manifest_path.parent / "controller.stderr.log").write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        raise ContractError("ENGINE_COMMAND_FAILED", detail={"returncode": proc.returncode, "stderr_tail": (proc.stderr or "")[-1200:]})
    if not result_path.is_file():
        raise ContractError("CONTROLLER_RESULT_MISSING", str(result_path))
    return result_path
