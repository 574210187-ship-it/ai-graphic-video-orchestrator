#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "graphic-video-orchestrator"


def main() -> int:
    parser = argparse.ArgumentParser(description="安装图文视频编排 Skill 到指定 AI 工具技能目录")
    parser.add_argument("--target", required=True, help="目标技能根目录，例如 ~/.codex/skills 或 Harness 自定义技能目录")
    parser.add_argument("--replace", action="store_true", help="目标已存在时先替换")
    args = parser.parse_args()

    root = Path(args.target).expanduser().resolve()
    target = root / SOURCE.name
    root.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not args.replace:
            raise SystemExit(f"目标已存在：{target}；确认后使用 --replace")
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    shutil.copytree(SOURCE, target)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
