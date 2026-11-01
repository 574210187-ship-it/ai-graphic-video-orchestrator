from __future__ import annotations

import json
from pathlib import Path

from gvflow.config import load_config
from gvflow.queue import discover_candidates, make_provider


def write_config(tmp_path: Path, records: dict) -> dict:
    fixture = tmp_path / "records.json"
    fixture.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        """
schema_version: 1
project: {name: test, actor_id: actor-test, runs_dir: ./runs}
production: {enabled: false, single_writer_required: true, max_attempts_per_record: 3, continue_after_record_failure: true}
provider: {type: fixture, fixture_file: ./records.json}
fields:
  classification: 二次分类型
  classification_value: 图文
  source_priority: [人工_对标视频, 对标视频, 对标视频、图文]
  product: 成品
  published: 已发布
  status: 状态
  completed_status: 完成视频
  note: zed备注
  execution_log: 执行记录
queue:
  mode: both_output_columns_without_video
  video_extensions: [.mp4, .mov, .webm]
  denylist: []
business: {profile_name: test, route_config: ./business.yaml, stage0_command: [], planner_command: []}
engine: {name: fixture, command: [], timeout_seconds: 60}
writeback: {replace_same_name: false, delete_local_media_after_verified_readback: true}
""".strip(),
        encoding="utf-8",
    )
    return load_config(config)


def row(record_id: str, *, product=None, published=None, sources=None, route="single_no_lawyer") -> dict:
    return {
        "record_id": record_id,
        "fields": {
            "二次分类型": "图文",
            "人工_对标视频": sources if sources is not None else [{"name": "src.mp4", "file_token": f"tok-{record_id}"}],
            "成品": product or [],
            "已发布": published or [],
            "状态": "未制作",
            "zed备注": "",
            "执行记录": "",
            "测试路线": route,
        },
    }


def test_discover_requires_both_output_fields_without_video(tmp_path: Path):
    records = {
        "files": {"tok-a": "source.bin", "tok-b": "source.bin", "tok-c": "source.bin"},
        "records": [
            row("a"),
            row("b", product=[{"name": "done.mp4", "file_token": "p1"}]),
            row("c", published=[{"name": "published.mov", "file_token": "p2"}]),
        ],
    }
    (tmp_path / "source.bin").write_bytes(b"source")
    config = write_config(tmp_path, records)
    candidates, blocked = discover_candidates(make_provider(config), config)
    assert [item.record_id for item in candidates] == ["a"]
    assert blocked == []


def test_non_unique_source_is_blocked_not_claimed(tmp_path: Path):
    records = {
        "files": {},
        "records": [row("a", sources=[{"name": "a.mp4", "file_token": "1"}, {"name": "b.mp4", "file_token": "2"}])],
    }
    config = write_config(tmp_path, records)
    candidates, blocked = discover_candidates(make_provider(config), config)
    assert candidates == []
    assert blocked[0]["error_code"] == "SOURCE_NOT_UNIQUE"
