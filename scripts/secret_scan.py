#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORE_PARTS = {".git", ".venv", "__pycache__", "runs", "downloads", "artifacts"}
TEXT_SUFFIXES = {".py", ".js", ".mjs", ".json", ".yaml", ".yml", ".md", ".toml", ".sh", ".txt"}
PATTERNS = {
    "secret_like": re.compile(r"(?i)(app_secret|access_token|webhook/send\?key=)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,}"),
    "absolute_private_path": re.compile(r"/(Users|home)/[^/\s]+/"),
    "feishu_app_secret": re.compile(r"(?i)cli_[a-z0-9]{10,}.*(?:secret|token)"),
}


def main() -> int:
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORE_PARTS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append({"file": str(path.relative_to(ROOT)), "rule": name, "line": text.count("\n", 0, match.start()) + 1})
    if findings:
        for item in findings:
            print(f"{item['rule']} {item['file']}:{item['line']}")
        return 1
    print("secret-scan: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
