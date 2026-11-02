from __future__ import annotations

from pathlib import Path

from gvflow.config import load_config


def test_windows_harness_example_parses_without_resolving_secret():
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "config" / "jiang-lawyer-harness.windows.example.yaml")

    assert config["provider"]["secret"]["backend"] == "windows_credential"
    assert config["provider"]["secret"]["target"] == "gvflow-feishu-app-secret"
    assert config["provider"]["app_id"] == "replace-feishu-app-id"
    assert config["provider"]["secret"]["account"] == "replace-feishu-app-id"
    assert config["provider"]["app_token"] == "replace-base-app-token"
    assert config["provider"]["table_id"] == "replace-business-table-id"
    assert config["production"]["enabled"] is False
