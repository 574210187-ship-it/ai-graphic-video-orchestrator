from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import ContractError
from .models import Artifact


OUTPUT_NAMES = {
    "01": "branch01_final_animation.mp4",
    "02": "branch02_final_animation.mp4",
    "lawyer": "lawyer_final_animation.mp4",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_mp4(path: Path, *, minimum_bytes: int = 200_000) -> tuple[int, str]:
    if not path.is_file():
        raise ContractError("VIDEO_ARTIFACT_MISSING", str(path))
    size = path.stat().st_size
    if size < minimum_bytes:
        raise ContractError("VIDEO_ARTIFACT_TOO_SMALL", str(path), detail={"bytes": size})
    with path.open("rb") as stream:
        head = stream.read(12)
    if len(head) < 12 or head[4:8] != b"ftyp":
        raise ContractError("VIDEO_ARTIFACT_NOT_MP4", str(path))
    return size, sha256_file(path)


def expected_branches(route: str) -> list[str]:
    if route in {"single_no_lawyer", "multi_no_lawyer"}:
        return ["01", "02"]
    if route == "single_lawyer":
        return ["lawyer"]
    raise ContractError("ROUTE_NOT_EXECUTABLE", route)


def load_and_validate_controller_result(path: Path, *, minimum_bytes: int = 200_000) -> tuple[dict, list[Artifact]]:
    if not path.is_file():
        raise ContractError("CONTROLLER_RESULT_MISSING", str(path))
    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("ok"):
        raise ContractError("CONTROLLER_REPORTED_FAILURE", detail=result.get("errors"))
    route = str(result.get("route") or "")
    required = expected_branches(route)
    raw_artifacts = result.get("artifacts") or []
    by_branch = {str(item.get("branch")): item for item in raw_artifacts if isinstance(item, dict)}
    if sorted(by_branch) != sorted(required):
        raise ContractError("ARTIFACT_BRANCH_SET_MISMATCH", detail={"expected": required, "actual": sorted(by_branch)})
    artifacts = []
    for branch in required:
        raw = by_branch[branch]
        path_value = Path(str(raw.get("path") or "")).expanduser()
        if not path_value.is_absolute():
            raise ContractError("ARTIFACT_PATH_NOT_ABSOLUTE", str(path_value))
        size, digest = validate_mp4(path_value, minimum_bytes=minimum_bytes)
        expected_name = OUTPUT_NAMES[branch]
        if path_value.name != expected_name:
            renamed = path_value.with_name(expected_name)
            if renamed.exists() and renamed.resolve() != path_value.resolve():
                raise ContractError("ARTIFACT_RENAME_TARGET_EXISTS", str(renamed))
            path_value.rename(renamed)
            path_value = renamed
        artifacts.append(
            Artifact(
                branch=branch,
                path=str(path_value.resolve()),
                name=expected_name,
                size=size,
                sha256=digest,
                chat_url=raw.get("chat_url"),
            )
        )
    if len(artifacts) == 2 and artifacts[0].sha256 == artifacts[1].sha256:
        raise ContractError("BRANCH_CONTENT_DUPLICATE", detail={"sha256": artifacts[0].sha256})
    return result, artifacts
