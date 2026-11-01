from __future__ import annotations

from gvflow.doctor import run_doctor

from test_queue import row, write_config


class UnhealthyProvider:
    def doctor(self) -> dict:
        return {"ok": False, "provider": "fixture", "error_code": "READ_PERMISSION_MISSING"}


def test_doctor_preserves_provider_failure(monkeypatch, tmp_path):
    records = {"files": {"tok-normal": "source.bin"}, "records": [row("normal")]}
    (tmp_path / "source.bin").write_bytes(b"fixture-media")
    config = write_config(tmp_path, records)
    monkeypatch.setattr("gvflow.doctor.make_provider", lambda _config: UnhealthyProvider())
    monkeypatch.setattr("gvflow.doctor.shutil.which", lambda name: f"/fixture/{name}")

    result = run_doctor(config)

    assert result["ok"] is False
    provider_check = next(item for item in result["checks"] if item["name"] == "provider")
    assert provider_check["ok"] is False
    assert provider_check["detail"]["error_code"] == "READ_PERMISSION_MISSING"
