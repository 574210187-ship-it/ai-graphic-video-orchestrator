from __future__ import annotations

from pathlib import Path

import yaml

from .config import resolve_path
from .errors import ConfigError


def load_business_profile(config: dict) -> tuple[Path, dict]:
    path = resolve_path(config, config["business"]["route_config"])
    if not path.is_file():
        raise ConfigError("BUSINESS_PROFILE_NOT_FOUND", str(path))
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ConfigError("BUSINESS_PROFILE_INVALID", str(path))
    return path, value
