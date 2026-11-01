from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from gvflow.artifacts import sha256_file
from gvflow.stage0_contract import finalize_stage0
from gvflow.stage0_media import prepare_stage0


def test_static_image_stage0_exports_one_reference_page(tmp_path: Path, monkeypatch):
    def missing_ffprobe(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr("gvflow.stage0_media.subprocess.run", missing_ffprobe)
    source = tmp_path / "source.png"
    Image.new("RGB", (120, 200), "navy").save(source)
    events = tmp_path / "events.jsonl"
    task_path = tmp_path / "task_manifest.json"
    task = {
        "schema_version": 1,
        "run_id": "run-test",
        "record_id": "rec-test",
        "actor_id": "actor-test",
        "state": "SOURCE_DOWNLOADED",
        "source": {"local_path": str(source), "sha256": sha256_file(source)},
        "events": str(events),
    }
    task_path.write_text(json.dumps(task), encoding="utf-8")
    stage0 = prepare_stage0(task_path)
    assert stage0["media_type"] == "image"
    assert [item["frame_id"] for item in stage0["candidates"]] == ["I001"]
    assert Path(stage0["contact_sheet"]).is_file()

    decision = tmp_path / "decision.json"
    decision.write_text(
        json.dumps({
            "source_sha256": task["source"]["sha256"],
            "route": "single_no_lawyer",
            "confidence": 0.99,
            "selected_frames": ["I001"],
        }),
        encoding="utf-8",
    )
    result = finalize_stage0(task_path, decision)
    assert result["route"] == "single_no_lawyer"
    assert Path(result["reference_pages"][0]["path"]).name == "对标完整页_01.png"
