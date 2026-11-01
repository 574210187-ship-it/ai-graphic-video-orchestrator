from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .doctor import run_doctor
from .errors import GvflowError
from .stage0_contract import finalize_stage0
from .stage0_media import prepare_stage0
from .workflow import discover, drain, execute, prepare, record_controller_result, writeback


def emit(value: dict, code: int = 0) -> int:
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return code


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="gvflow")
    sub = root.add_subparsers(dest="command", required=True)

    command = sub.add_parser("doctor")
    command.add_argument("--config", required=True)
    command.add_argument("--offline", action="store_true")

    command = sub.add_parser("discover")
    command.add_argument("--config", required=True)

    command = sub.add_parser("prepare")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("finalize-stage0")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)
    command.add_argument("--decision-file", required=True)

    command = sub.add_parser("stage0-prepare")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("execute")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("plan")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("reserve-background")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("abort-background")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("record-result")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)
    command.add_argument("--route", required=True)
    command.add_argument("--artifact", action="append", required=True, help="branch:/absolute/path.mp4")
    command.add_argument("--chat-url", action="append", default=[], help="branch:https://chat-url")

    command = sub.add_parser("writeback")
    command.add_argument("--config", required=True)
    command.add_argument("--record-id", required=True)

    command = sub.add_parser("drain")
    command.add_argument("--config", required=True)
    command.add_argument("--limit", type=int)

    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "doctor":
            result = run_doctor(config, offline=args.offline)
            return emit(result, 0 if result["ok"] else 2)
        if args.command == "discover":
            return emit(discover(config))
        if args.command == "prepare":
            return emit(prepare(config, args.record_id))
        if args.command == "finalize-stage0":
            runs = Path(config["project"]["runs_dir"])
            if not runs.is_absolute():
                runs = Path(config["_config_dir"]) / runs
            manifest = finalize_stage0(runs.resolve() / args.record_id / "task_manifest.json", Path(args.decision_file).expanduser().resolve())
            return emit({"ok": True, "record_id": args.record_id, "route": manifest["route"]})
        if args.command == "stage0-prepare":
            runs = Path(config["project"]["runs_dir"])
            if not runs.is_absolute():
                runs = Path(config["_config_dir"]) / runs
            result = prepare_stage0(runs.resolve() / args.record_id / "task_manifest.json")
            return emit({"ok": True, "record_id": args.record_id, "stage0": result})
        if args.command == "execute":
            return emit(execute(config, args.record_id))
        if args.command == "plan":
            from .planner import build_execution_plan

            runs = Path(config["project"]["runs_dir"])
            if not runs.is_absolute():
                runs = Path(config["_config_dir"]) / runs
            plan = build_execution_plan(config, runs.resolve() / args.record_id / "task_manifest.json")
            return emit({"ok": True, "record_id": args.record_id, "plan": plan})
        if args.command == "reserve-background":
            from .rotation import reserve_background

            return emit({"ok": True, **reserve_background(config, args.record_id)})
        if args.command == "abort-background":
            from .rotation import abort_background

            return emit({"ok": True, "state": abort_background(config, args.record_id)})
        if args.command == "record-result":
            return emit(record_controller_result(
                config,
                args.record_id,
                route=args.route,
                artifact_specs=args.artifact,
                chat_specs=args.chat_url,
            ))
        if args.command == "writeback":
            return emit(writeback(config, args.record_id))
        if args.command == "drain":
            result = drain(config, limit=args.limit)
            return emit(result, 0 if result["scope_drained"] else 3)
        return emit({"ok": False, "error_code": "COMMAND_UNSUPPORTED"}, 2)
    except GvflowError as exc:
        return emit(exc.as_dict(), 2)
    except Exception as exc:
        return emit({"ok": False, "error_code": "UNHANDLED_ERROR", "message": str(exc)}, 2)


if __name__ == "__main__":
    raise SystemExit(main())
