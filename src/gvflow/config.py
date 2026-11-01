from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError


ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if not isinstance(value, str):
        return value

    missing = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        resolved = os.environ.get(name)
        if resolved is None:
            missing.append(name)
            return match.group(0)
        return resolved

    resolved = ENV_RE.sub(replace, value)
    if missing:
        raise ConfigError("CONFIG_ENV_MISSING", f"缺少环境变量：{','.join(sorted(set(missing)))}")
    return resolved


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ConfigError("CONFIG_NOT_FOUND", str(path)) from exc
    except yaml.YAMLError as exc:
        raise ConfigError("CONFIG_YAML_INVALID", f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("CONFIG_ROOT_MUST_BE_OBJECT", str(path))
    return data


def load_config(path: str | Path) -> dict:
    path = Path(path).expanduser().resolve()
    raw = _read_yaml(path)
    merged: dict = {}
    parents = raw.pop("extends", [])
    if isinstance(parents, str):
        parents = [parents]
    for parent in parents:
        parent_path = Path(parent)
        if not parent_path.is_absolute():
            parent_path = path.parent / parent_path
        merged = _deep_merge(merged, load_config(parent_path))
    merged = _deep_merge(merged, raw)
    merged = _expand_env(merged)
    merged["_config_path"] = str(path)
    merged["_config_dir"] = str(path.parent)
    validate_config(merged)
    return merged


def resolve_path(config: dict, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(config["_config_dir"]) / path
    return path.resolve()


def validate_config(config: dict) -> None:
    if config.get("schema_version") != 1:
        raise ConfigError("CONFIG_SCHEMA_UNSUPPORTED", str(config.get("schema_version")))
    for section in ("project", "production", "provider", "fields", "queue", "engine", "writeback"):
        if not isinstance(config.get(section), dict):
            raise ConfigError("CONFIG_SECTION_MISSING", section)
    fields = config["fields"]
    required_fields = (
        "classification",
        "classification_value",
        "source_priority",
        "product",
        "published",
        "status",
        "completed_status",
        "note",
        "execution_log",
    )
    for key in required_fields:
        if not fields.get(key):
            raise ConfigError("CONFIG_FIELD_MAPPING_MISSING", key)
    if not isinstance(fields["source_priority"], list) or not fields["source_priority"]:
        raise ConfigError("CONFIG_SOURCE_PRIORITY_INVALID")
    if not config["project"].get("actor_id"):
        raise ConfigError("CONFIG_ACTOR_ID_REQUIRED")
