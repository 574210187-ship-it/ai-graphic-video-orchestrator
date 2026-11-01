from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .queue import make_provider


def run_doctor(config: dict, *, offline: bool = False) -> dict:
    checks = []

    def add(name: str, ok: bool, detail: object = None) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    runs = Path(config["project"]["runs_dir"])
    if not runs.is_absolute():
        runs = Path(config["_config_dir"]) / runs
    runs.mkdir(parents=True, exist_ok=True)
    add("runs_dir_writable", os.access(runs, os.W_OK), str(runs.resolve()))
    python_path = Path(sys.executable)
    add("python", python_path.is_file(), str(python_path))
    add("ffprobe", bool(shutil.which("ffprobe")), shutil.which("ffprobe") or "视频第0阶段需要FFmpeg/ffprobe")

    engine = config["engine"]
    if engine.get("name") == "fixture":
        add("engine_fixture", True)
    elif engine.get("mode") == "agent_native":
        add("engine_agent_native", True, engine.get("name"))
    else:
        command = engine.get("command") or []
        first = command[0] if isinstance(command, list) and command else None
        add("engine_command_configured", bool(first), first)
        if first and "{" not in str(first):
            add("engine_command_available", bool(shutil.which(str(first)) or Path(str(first)).exists()), first)

    if offline:
        add("provider", True, "offline-skipped")
    else:
        try:
            provider_result = make_provider(config).doctor()
            add("provider", bool(provider_result.get("ok")), provider_result)
        except Exception as exc:
            add("provider", False, str(exc))
    if config["provider"].get("type") != "fixture":
        add("production_write_gate_safe", True, "enabled" if config["production"].get("enabled") else "disabled-read-only")
        add("single_writer_required", bool(config["production"].get("single_writer_required")), config["production"].get("single_writer_required"))
    return {"ok": all(item["ok"] for item in checks), "offline": offline, "checks": checks}
