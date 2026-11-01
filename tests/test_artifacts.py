from __future__ import annotations

import json
from pathlib import Path

import pytest

from gvflow.artifacts import load_and_validate_controller_result
from gvflow.errors import ContractError


def fake_mp4(path: Path, marker: bytes):
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + marker * 220_000)


def test_duplicate_ordinary_branches_are_rejected(tmp_path: Path):
    first = tmp_path / "branch01_final_animation.mp4"
    second = tmp_path / "branch02_final_animation.mp4"
    fake_mp4(first, b"a")
    second.write_bytes(first.read_bytes())
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps({"ok": True, "route": "single_no_lawyer", "artifacts": [{"branch": "01", "path": str(first)}, {"branch": "02", "path": str(second)}]}),
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="BRANCH_CONTENT_DUPLICATE"):
        load_and_validate_controller_result(result)
