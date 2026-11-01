from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from .artifacts import sha256_file
from .errors import ContractError
from .events import append_event, atomic_json


def _media_modules():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError as exc:
        raise ContractError("MEDIA_EXTRA_NOT_INSTALLED", "请安装 pip install -e '.[media]'") from exc
    return cv2, np, Image, ImageDraw, ImageFont


def _probe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode:
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def _detect_media(path: Path, probe: dict) -> str:
    _, _, Image, _, _ = _media_modules()
    try:
        with Image.open(path) as image:
            image.verify()
        return "image"
    except Exception:
        pass
    if any(stream.get("codec_type") == "video" for stream in probe.get("streams", [])):
        return "video"
    raise ContractError("UNSUPPORTED_REFERENCE_MEDIA", str(path))


def _read_frame(cv2, capture, seconds: float):
    capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, seconds) * 1000.0)
    ok, frame = capture.read()
    return frame if ok else None


def _candidate_times(path: Path, duration: float) -> list[tuple[float, float]]:
    cv2, np, _, _, _ = _media_modules()
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ContractError("VIDEO_OPEN_FAILED", str(path))
    scan_count = min(72, max(18, int(math.ceil(duration * 2))))
    times = np.linspace(0.0, max(0.01, duration - 0.05), scan_count).tolist()
    valid: list[float] = []
    small = []
    for seconds in times:
        frame = _read_frame(cv2, capture, seconds)
        if frame is None:
            continue
        valid.append(float(seconds))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small.append(cv2.resize(gray, (160, 284), interpolation=cv2.INTER_AREA))
    capture.release()
    if not small:
        raise ContractError("VIDEO_HAS_NO_DECODABLE_FRAMES", str(path))
    scores = [0.0]
    for current, previous in zip(small[1:], small[:-1]):
        scores.append(float(np.mean(cv2.absdiff(current, previous))))
    base_count = min(16, max(8, int(math.ceil(duration / 2.5))))
    selected = set(np.linspace(0, len(valid) - 1, min(base_count, len(valid)), dtype=int).tolist())
    transitions = sorted(range(1, len(valid)), key=lambda index: scores[index], reverse=True)[:8]
    for index in transitions:
        selected.add(index)
        if index + 1 < len(valid):
            selected.add(index + 1)
    ordered = sorted(selected)
    if len(ordered) > 24:
        ordered = sorted(set(np.linspace(0, len(valid) - 1, 16, dtype=int).tolist()) | set(transitions))[:24]
    return [(valid[index], scores[index]) for index in ordered]


def _make_contact_sheet(entries: list[dict], target: Path) -> None:
    _, _, Image, ImageDraw, ImageFont = _media_modules()
    columns = 4
    thumb_width, thumb_height, label_height = 280, 498, 34
    rows = math.ceil(len(entries) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for offset, entry in enumerate(entries):
        with Image.open(entry["path"]) as source:
            source = source.convert("RGB")
            source.thumbnail((thumb_width, thumb_height))
            x = offset % columns * thumb_width + (thumb_width - source.width) // 2
            y = offset // columns * (thumb_height + label_height)
            sheet.paste(source, (x, y))
        draw.text((offset % columns * thumb_width + 6, y + thumb_height + 8), f"{entry['frame_id']} t={entry['time_seconds']:.3f}s", fill="black", font=font)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, format="JPEG", quality=88)


def prepare_stage0(task_manifest_path: Path) -> dict:
    task_manifest_path = task_manifest_path.resolve()
    task = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    source = Path(task["source"]["local_path"])
    if sha256_file(source) != task["source"]["sha256"]:
        raise ContractError("STAGE0_SOURCE_SHA_MISMATCH")
    out_dir = task_manifest_path.parent / "stage0"
    candidate_dir = out_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    probe = _probe(source)
    media_type = _detect_media(source, probe)
    entries = []
    cv2, _, Image, _, _ = _media_modules()
    if media_type == "image":
        target = candidate_dir / "I001.png"
        with Image.open(source) as image:
            image.convert("RGB").save(target, format="PNG")
            width, height = image.size
        entries.append({"frame_id": "I001", "time_seconds": 0.0, "scene_change_score": 0.0, "width": width, "height": height, "path": str(target.resolve())})
        duration = None
    else:
        duration = float((probe.get("format") or {}).get("duration") or 0.0)
        if duration <= 0:
            raise ContractError("VIDEO_DURATION_INVALID")
        capture = cv2.VideoCapture(str(source))
        for seconds, score in _candidate_times(source, duration):
            frame = _read_frame(cv2, capture, seconds)
            if frame is None:
                continue
            frame_id = f"F{len(entries) + 1:03d}"
            target = candidate_dir / f"{frame_id}.png"
            if not cv2.imwrite(str(target), frame):
                raise ContractError("CANDIDATE_WRITE_FAILED", frame_id)
            height, width = frame.shape[:2]
            entries.append({"frame_id": frame_id, "time_seconds": round(seconds, 6), "scene_change_score": round(score, 4), "width": width, "height": height, "path": str(target.resolve())})
        capture.release()
    if not entries:
        raise ContractError("STAGE0_NO_CANDIDATES")
    contact_sheet = out_dir / "stage0_contact_sheet.jpg"
    _make_contact_sheet(entries, contact_sheet)
    manifest = {
        "schema_version": 1,
        "record_id": task["record_id"],
        "source_sha256": task["source"]["sha256"],
        "media_type": media_type,
        "duration_seconds": duration,
        "contact_sheet": str(contact_sheet.resolve()),
        "candidates": entries,
        "decision_required": {
            "route": "single_no_lawyer|multi_no_lawyer|single_lawyer|multi_lawyer_suspended",
            "selected_frames": "one final full-text frame per page in order",
            "confidence": "0.0-1.0",
        },
    }
    target = out_dir / "stage0_manifest.json"
    atomic_json(target, manifest)
    task.update({"state": "STAGE0_CANDIDATES_READY", "stage0_manifest": str(target.resolve()), "stage0_contact_sheet": str(contact_sheet.resolve())})
    atomic_json(task_manifest_path, task)
    append_event(
        Path(task["events"]),
        run_id=task["run_id"],
        record_id=task["record_id"],
        actor_id=task["actor_id"],
        state="STAGE0_CANDIDATES_READY",
        media_type=media_type,
        candidate_count=len(entries),
        contact_sheet=str(contact_sheet.resolve()),
    )
    return manifest
