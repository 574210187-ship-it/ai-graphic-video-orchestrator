from __future__ import annotations

import json
from pathlib import Path

from .business import load_business_profile
from .errors import ContractError
from .events import atomic_json


RULE_KEYS = {
    "single_no_lawyer": [("01", "single_01"), ("02", "single_02")],
    "multi_no_lawyer": [("01", "multi_01"), ("02", "multi_02")],
    "single_lawyer": [("lawyer", "single_lawyer")],
}


def _image_prompt(route: str, branch: str, rule: dict, references: list[dict], selected_asset: str | None) -> str:
    page_names = [Path(item["path"]).name for item in references]
    source_line = (
        f"按编号查看本轮完整对标图片 `{page_names[0]}` 至 `{page_names[-1]}`。"
        if len(page_names) > 1
        else f"查看本轮唯一完整对标图片 `{page_names[0]}`。"
    )
    asset_line = ""
    if branch == "01":
        asset_line = f"\n本轮唯一纯蓝色背景必须从Space准确路径读取：{selected_asset}。不得改选、不得读取背景ZIP。"
    elif branch == "lawyer":
        asset_line = f"\n本轮唯一人物图片必须从Space准确路径读取：{selected_asset}。不得改选、不得读取人物ZIP。"
    outputs = (
        "生成共用背景图1张、按页顺序的透明文字图N张、按页顺序的成品图N张。"
        if route == "multi_no_lawyer"
        else "生成背景图1张、透明文字图1张、成品图1张。"
    )
    return (
        f"读取并完整执行Space现行文件：{rule['path']}。当前核验版本为{rule['version']}，不得读取同名旧版本。\n"
        f"先完整读取MD，再{source_line}{asset_line}\n"
        f"使用Imagegen严格按MD执行：{outputs}\n"
        "默认逐字使用对标完整页；只有task_manifest中的用户授权替换清单允许局部替换，清单外不得改写。"
        "不得用代码、JSON、PIL、HTML或程序化排版代替Imagegen。"
    )


def _video_prompt(route: str, branch: str, zip_path: str, source_is_video: bool) -> str:
    source_line = "本步骤只新上传原对标视频一次。" if source_is_video else "静态图片源本步骤不新增附件。"
    layers = (
        "只使用本聊天上一步的共用背景和全部透明文字图；不得使用多页成品图。"
        if route == "multi_no_lawyer"
        else "使用本聊天上一步生成或指定的背景图、透明文字图和成品图。"
    )
    return (
        f"继续当前{branch}分支聊天，不要新开聊天。{source_line}{layers}不得调用其他分支聊天图片。\n"
        f"只读取并严格执行资料库正式包：{zip_path}。完整读取包内《执行说明.txt》，最终只交付MP4.zip。"
        "不要使用根目录或任何其他同名ZIP，不生成HTML，不修改规则包。"
    )


def build_execution_plan(config: dict, manifest_path: Path) -> dict:
    _, profile = load_business_profile(config)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    route = manifest.get("route")
    if route not in RULE_KEYS:
        raise ContractError("PLAN_ROUTE_UNSUPPORTED", str(route))
    rules = (profile.get("space") or {}).get("image_rules") or {}
    video_rules = (profile.get("space") or {}).get("video_rules") or {}
    references = manifest.get("reference_pages") or []
    if not references:
        raise ContractError("REFERENCE_PAGES_REQUIRED")
    decision = manifest.get("stage0_decision") or {}
    selected_background = (manifest.get("background_reservation") or {}).get("space_path") or decision.get("selected_background_space_path")
    selected_portrait = decision.get("selected_portrait_space_path")
    if route in {"single_no_lawyer", "multi_no_lawyer"} and not selected_background:
        raise ContractError("BACKGROUND_RESERVATION_REQUIRED")
    if route == "single_lawyer" and not selected_portrait:
        raise ContractError("PORTRAIT_SELECTION_REQUIRED")
    source_is_video = (manifest.get("stage0_media_type") or "") == "video"
    actions = []
    for branch, key in RULE_KEYS[route]:
        rule = rules.get(key)
        if not isinstance(rule, dict) or not rule.get("path") or not rule.get("version"):
            raise ContractError("IMAGE_RULE_CONFIG_MISSING", key)
        asset = selected_background if branch == "01" else selected_portrait if branch == "lawyer" else None
        actions.append({
            "step_id": f"{branch}_image",
            "branch": branch,
            "phase": "image",
            "open_new_chat": True,
            "attachments": [{"path": item["path"], "name": Path(item["path"]).name} for item in references],
            "prompt": _image_prompt(route, branch, rule, references, asset),
        })
        video_kind = "multi" if route == "multi_no_lawyer" else "single"
        zip_path = video_rules.get(video_kind)
        if not zip_path:
            raise ContractError("VIDEO_RULE_CONFIG_MISSING", video_kind)
        actions.append({
            "step_id": f"{branch}_video",
            "branch": branch,
            "phase": "video",
            "open_new_chat": False,
            "attachments": [{"path": manifest["source"]["local_path"], "name": manifest["source"]["name"]}] if source_is_video else [],
            "prompt": _video_prompt(route, branch, zip_path, source_is_video),
        })
    plan = {
        "schema_version": 1,
        "record_id": manifest["record_id"],
        "route": route,
        "engine": manifest["engine"],
        "actions": actions,
        "controller_result": manifest["controller_result"],
    }
    target = manifest_path.parent / "execution_plan.json"
    atomic_json(target, plan)
    manifest.update({"state": "PLANNED", "execution_plan": str(target.resolve())})
    atomic_json(manifest_path, manifest)
    return plan
