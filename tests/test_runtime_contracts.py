from __future__ import annotations

import json
from pathlib import Path

import pytest

from gvflow.errors import ContractError
from gvflow.manifest import update_manifest
from gvflow.planner import build_execution_plan
from gvflow.queue import make_provider
from gvflow.rotation import abort_background, commit_background, reserve_background
from gvflow.workflow import prepare, record_controller_result, verify_write_access, writeback

from test_artifacts import fake_mp4
from test_queue import row, write_config


def write_business_profile(tmp_path: Path) -> None:
    (tmp_path / "business.yaml").write_text(
        """
schema_version: 1
profile_name: test
space:
  image_rules:
    single_01: {path: /space/single01.md, version: v1}
    single_02: {path: /space/single02.md, version: v1}
    multi_01: {path: /space/multi01.md, version: v1}
    multi_02: {path: /space/multi02.md, version: v1}
    single_lawyer: {path: /space/lawyer.md, version: v1}
  video_rules:
    single: /space/video-single.zip
    multi: /space/video-multi.zip
  backgrounds: [/space/blue01.png, /space/blue02.png, /space/blue03.png]
  portraits: [/space/lawyer01.png]
assets:
  rotation_state: ./rotation.json
""".strip(),
        encoding="utf-8",
    )


def prepared_config(tmp_path: Path) -> tuple[dict, Path]:
    records = {"files": {"tok-normal": "source.bin"}, "records": [row("normal")]}
    (tmp_path / "source.bin").write_bytes(b"fixture-media")
    write_business_profile(tmp_path)
    config = write_config(tmp_path, records)
    prepare(config, "normal")
    manifest_path = tmp_path / "runs" / "normal" / "task_manifest.json"
    return config, manifest_path


def test_background_rotation_is_idempotent_and_commits_only_after_record(tmp_path: Path):
    config, _ = prepared_config(tmp_path)
    first = reserve_background(config, "normal")
    assert first["background_index"] == 1
    assert reserve_background(config, "normal")["space_path"] == "/space/blue01.png"
    with pytest.raises(ContractError, match="BACKGROUND_ROTATION_PENDING"):
        reserve_background(config, "other")
    abort_background(config, "normal")
    reserve_background(config, "normal")
    state = commit_background(config, "normal")
    assert state["next_index"] == 2
    assert state["pending"] is None


def test_planner_builds_isolated_branch_chats_and_reuses_each_chat_for_video(tmp_path: Path):
    config, manifest_path = prepared_config(tmp_path)
    reference = tmp_path / "runs" / "normal" / "对标完整页_01.png"
    reference.write_bytes(b"png-reference")
    update_manifest(
        manifest_path,
        route="single_no_lawyer",
        stage0_media_type="video",
        stage0_decision={"route": "single_no_lawyer"},
        reference_pages=[{"page": 1, "path": str(reference), "sha256": "fixture"}],
    )
    reserve_background(config, "normal")
    plan = build_execution_plan(config, manifest_path)
    assert [item["step_id"] for item in plan["actions"]] == ["01_image", "01_video", "02_image", "02_video"]
    assert plan["actions"][0]["open_new_chat"] is True
    assert plan["actions"][1]["open_new_chat"] is False
    assert plan["actions"][2]["open_new_chat"] is True
    assert plan["actions"][3]["open_new_chat"] is False
    assert len(plan["actions"][1]["attachments"]) == 1
    assert len(plan["actions"][3]["attachments"]) == 1


def test_partial_attachment_writeback_resumes_without_duplicate(tmp_path: Path):
    config, manifest_path = prepared_config(tmp_path)
    reference = tmp_path / "runs" / "normal" / "对标完整页_01.png"
    reference.write_bytes(b"png-reference")
    update_manifest(
        manifest_path,
        route="single_no_lawyer",
        stage0_media_type="image",
        stage0_decision={"route": "single_no_lawyer"},
        reference_pages=[{"page": 1, "path": str(reference), "sha256": "fixture"}],
    )
    reserve_background(config, "normal")
    first = tmp_path / "branch01_final_animation.mp4"
    second = tmp_path / "branch02_final_animation.mp4"
    fake_mp4(first, b"first")
    fake_mp4(second, b"second")
    record_controller_result(
        config,
        "normal",
        route="single_no_lawyer",
        artifact_specs=[f"01:{first}", f"02:{second}"],
        chat_specs=["01:https://chat.example/01", "02:https://chat.example/02"],
    )
    provider = make_provider(config)
    provider.attach_files("normal", "成品", [first])
    result = writeback(config, "normal")
    assert result["readback_verified"] is True
    fields = provider.get_record("normal")["fields"]
    assert [item["name"] for item in fields["成品"]] == [
        "branch01_final_animation.mp4",
        "branch02_final_animation.mp4",
    ]
    assert fields["状态"] == "完成视频"
    state = json.loads((tmp_path / "rotation.json").read_text(encoding="utf-8"))
    assert state["next_index"] == 2
    assert state["pending"] is None


def test_verify_write_access_uploads_reads_back_and_restores_empty_product(tmp_path: Path):
    config, _ = prepared_config(tmp_path)
    result = verify_write_access(config, "normal", confirmed_dedicated_test_record=True)
    assert result["attachment_upload_verified"] is True
    assert result["field_write_verified"] is True
    assert result["restored_to_original"] is True
    fields = make_provider(config).get_record("normal")["fields"]
    assert fields["\u6210\u54c1"] == []


def test_verify_write_access_requires_explicit_dedicated_record_confirmation(tmp_path: Path):
    config, _ = prepared_config(tmp_path)
    with pytest.raises(ContractError, match="DEDICATED_TEST_RECORD_CONFIRMATION_REQUIRED"):
        verify_write_access(config, "normal", confirmed_dedicated_test_record=False)
