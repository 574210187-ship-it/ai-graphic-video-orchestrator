from __future__ import annotations

import json
import shutil
from pathlib import Path

from .artifacts import sha256_file
from .errors import ContractError
from .events import append_event, atomic_json


ALLOWED_ROUTES = {"single_no_lawyer", "multi_no_lawyer", "single_lawyer"}


def finalize_stage0(manifest_path: Path, decision_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if decision.get("source_sha256") != manifest.get("source", {}).get("sha256"):
        raise ContractError("STAGE0_SOURCE_SHA_MISMATCH")
    route = decision.get("route")
    if route == "multi_lawyer" or route == "multi_lawyer_suspended":
        raise ContractError("MULTI_PAGE_LAWYER_SUSPENDED")
    if route not in ALLOWED_ROUTES:
        raise ContractError("STAGE0_ROUTE_INVALID", str(route))
    confidence = float(decision.get("confidence") or 0.0)
    if confidence < 0.70:
        raise ContractError("STAGE0_LOW_CONFIDENCE", detail={"confidence": confidence})
    references = decision.get("reference_pages") or []
    selected_frames = decision.get("selected_frames") or []
    if not references and selected_frames:
        stage0_path = Path(str(manifest.get("stage0_manifest") or ""))
        if not stage0_path.is_file():
            raise ContractError("STAGE0_MANIFEST_MISSING", str(stage0_path))
        stage0 = json.loads(stage0_path.read_text(encoding="utf-8"))
        candidates = {item["frame_id"]: item for item in stage0.get("candidates") or []}
        out_dir = manifest_path.parent / "stage0" / "reference_pages"
        out_dir.mkdir(parents=True, exist_ok=True)
        references = []
        for index, raw in enumerate(selected_frames, 1):
            frame_id = raw.get("frame_id") if isinstance(raw, dict) else raw
            if frame_id not in candidates:
                raise ContractError("STAGE0_SELECTED_FRAME_INVALID", str(frame_id))
            target = out_dir / f"对标完整页_{index:02d}.png"
            shutil.copy2(candidates[frame_id]["path"], target)
            references.append({"path": str(target.resolve()), "frame_id": frame_id})
    if not references:
        raise ContractError("REFERENCE_PAGES_REQUIRED")
    normalized = []
    for index, item in enumerate(references, 1):
        path = Path(str(item.get("path") or "")).expanduser()
        if not path.is_absolute() or not path.is_file():
            raise ContractError("REFERENCE_PAGE_MISSING", str(path))
        normalized.append({"page": index, "path": str(path.resolve()), "sha256": sha256_file(path), "frame_id": item.get("frame_id")})
    if route.startswith("single") and len(normalized) != 1:
        raise ContractError("SINGLE_ROUTE_REFERENCE_COUNT_INVALID", detail={"count": len(normalized)})
    if route.startswith("multi") and len(normalized) < 2:
        raise ContractError("MULTI_ROUTE_REFERENCE_COUNT_INVALID", detail={"count": len(normalized)})
    stage0_media_type = None
    stage0_path = Path(str(manifest.get("stage0_manifest") or ""))
    if stage0_path.is_file():
        stage0_media_type = json.loads(stage0_path.read_text(encoding="utf-8")).get("media_type")
    manifest.update({
        "state": "STAGE0_READY",
        "route": route,
        "stage0_decision": decision,
        "stage0_media_type": stage0_media_type,
        "reference_pages": normalized,
    })
    atomic_json(manifest_path, manifest)
    append_event(
        Path(manifest["events"]),
        run_id=manifest["run_id"],
        record_id=manifest["record_id"],
        actor_id=manifest["actor_id"],
        state="STAGE0_READY",
        route=route,
        confidence=confidence,
        reference_pages=normalized,
    )
    return manifest
