from __future__ import annotations

import json
from pathlib import Path

from gvflow.config import load_config
from gvflow.workflow import discover, drain

from test_queue import row, write_config


def test_fixture_drain_writes_and_reads_back_all_eligible_rows(tmp_path: Path):
    records = {
        "files": {
            "tok-normal": "source.bin",
            "tok-lawyer": "source.bin",
            "tok-existing": "source.bin",
        },
        "records": [
            row("normal", route="single_no_lawyer"),
            row("lawyer", route="single_lawyer"),
            row("existing", product=[{"name": "already.mp4", "file_token": "old", "size": 10}]),
        ],
    }
    (tmp_path / "source.bin").write_bytes(b"fixture-media")
    config = write_config(tmp_path, records)
    result = drain(config)
    assert result["scope_drained"] is True
    assert result["completed"] == ["normal", "lawyer"]
    assert result["remaining"] == []
    assert discover(config)["count"] == 0

    final = json.loads((tmp_path / "records.json").read_text(encoding="utf-8"))
    by_id = {item["record_id"]: item for item in final["records"]}
    normal_fields = by_id["normal"]["fields"]
    lawyer_fields = by_id["lawyer"]["fields"]
    assert normal_fields["状态"] == "完成视频"
    assert [item["name"] for item in normal_fields["成品"]] == [
        "branch01_final_animation.mp4",
        "branch02_final_animation.mp4",
    ]
    assert lawyer_fields["状态"] == "完成视频"
    assert [item["name"] for item in lawyer_fields["成品"]] == ["lawyer_final_animation.mp4"]
    assert "writeback=verified" in normal_fields["执行记录"]


def test_record_failure_does_not_stop_later_rows(tmp_path: Path):
    records = {
        "files": {"tok-bad": "source.bin", "tok-good": "source.bin"},
        "records": [row("bad", route="multi_lawyer"), row("good", route="single_no_lawyer")],
    }
    (tmp_path / "source.bin").write_bytes(b"fixture-media")
    config = write_config(tmp_path, records)
    result = drain(config)
    assert result["scope_drained"] is False
    assert result["completed"] == ["good"]
    assert result["failed"][0]["record_id"] == "bad"
    assert result["remaining"] == ["bad"]
