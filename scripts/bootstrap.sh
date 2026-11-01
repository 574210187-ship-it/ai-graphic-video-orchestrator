#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[test,media]'

echo "安装完成：$repo_dir/.venv"
echo "下一步：cp config/example.yaml config/config.local.yaml"
