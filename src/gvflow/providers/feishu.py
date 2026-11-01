from __future__ import annotations

import json
import math
import mimetypes
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from ..errors import ConfigError, ProviderError
from .base import RecordProvider


UPLOAD_ALL_LIMIT = 20 * 1024 * 1024


def _secret_from_config(secret_config: dict, app_id: str) -> str:
    backend = secret_config.get("backend")
    if backend == "env":
        name = secret_config.get("name") or "FEISHU_APP_SECRET"
        value = os.environ.get(name)
        if not value:
            raise ConfigError("FEISHU_SECRET_ENV_MISSING", name)
        return value
    if backend == "macos_keychain":
        service = secret_config.get("service")
        account = secret_config.get("account") or app_id
        if not service:
            raise ConfigError("FEISHU_KEYCHAIN_SERVICE_REQUIRED")
        try:
            value = subprocess.check_output(
                ["/usr/bin/security", "find-generic-password", "-w", "-s", service, "-a", account],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise ProviderError("FEISHU_KEYCHAIN_SECRET_MISSING", f"service={service} account={account}") from exc
        if not value:
            raise ProviderError("FEISHU_KEYCHAIN_SECRET_EMPTY")
        return value
    if backend == "windows_credential":
        if os.name != "nt":
            raise ConfigError("FEISHU_WINDOWS_CREDENTIAL_REQUIRES_WINDOWS")
        target = str(secret_config.get("target") or "")
        expected_account = str(secret_config.get("account") or app_id)
        if not target:
            raise ConfigError("FEISHU_WINDOWS_CREDENTIAL_TARGET_REQUIRED")
        try:
            import ctypes
            from ctypes import wintypes

            class CredentialW(ctypes.Structure):
                _fields_ = [
                    ("Flags", wintypes.DWORD),
                    ("Type", wintypes.DWORD),
                    ("TargetName", wintypes.LPWSTR),
                    ("Comment", wintypes.LPWSTR),
                    ("LastWritten", wintypes.FILETIME),
                    ("CredentialBlobSize", wintypes.DWORD),
                    ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                    ("Persist", wintypes.DWORD),
                    ("AttributeCount", wintypes.DWORD),
                    ("Attributes", ctypes.c_void_p),
                    ("TargetAlias", wintypes.LPWSTR),
                    ("UserName", wintypes.LPWSTR),
                ]

            credential_pointer = ctypes.POINTER(CredentialW)()
            advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
            advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CredentialW))]
            advapi32.CredReadW.restype = wintypes.BOOL
            advapi32.CredFree.argtypes = [ctypes.c_void_p]
            if not advapi32.CredReadW(target, 1, 0, ctypes.byref(credential_pointer)):
                raise ProviderError("FEISHU_WINDOWS_CREDENTIAL_MISSING", f"target={target}", detail={"winerror": ctypes.get_last_error()})
            try:
                credential = credential_pointer.contents
                if expected_account and credential.UserName != expected_account:
                    raise ProviderError(
                        "FEISHU_WINDOWS_CREDENTIAL_ACCOUNT_MISMATCH",
                        detail={"target": target, "expected": expected_account, "actual": credential.UserName},
                    )
                blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
                value = blob.decode("utf-16-le")
            finally:
                advapi32.CredFree(credential_pointer)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("FEISHU_WINDOWS_CREDENTIAL_READ_FAILED", f"target={target}") from exc
        if not value:
            raise ProviderError("FEISHU_WINDOWS_CREDENTIAL_EMPTY", f"target={target}")
        return value
    raise ConfigError("FEISHU_SECRET_BACKEND_UNSUPPORTED", str(backend))


class FeishuProvider(RecordProvider):
    def __init__(self, config: dict):
        provider = config["provider"]
        self.config = config
        self.app_id = str(provider.get("app_id") or "")
        self.app_token = str(provider.get("app_token") or "")
        self.table_id = str(provider.get("table_id") or "")
        self.api_root = str(provider.get("api_root") or "https://open.feishu.cn/open-apis").rstrip("/")
        if not all((self.app_id, self.app_token, self.table_id)):
            raise ConfigError("FEISHU_PROVIDER_IDENTIFIERS_REQUIRED")
        self._secret_config = provider.get("secret") or {}
        self._token: str | None = None

    @property
    def token(self) -> str:
        if self._token is None:
            secret = _secret_from_config(self._secret_config, self.app_id)
            result = self._json_request(
                "POST",
                "/auth/v3/tenant_access_token/internal",
                payload={"app_id": self.app_id, "app_secret": secret},
                authenticated=False,
            )
            self._token = result.get("tenant_access_token")
            if not self._token:
                raise ProviderError("FEISHU_TENANT_TOKEN_MISSING")
        return self._token

    def _json_request(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        query: dict | None = None,
        authenticated: bool = True,
        timeout: int = 60,
        retries: int = 2,
    ) -> dict:
        url = f"{self.api_root}{path}"
        if query:
            url += "?" + urllib.parse.urlencode({key: value for key, value in query.items() if value is not None})
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last: Exception | None = None
        for attempt in range(retries + 1):
            request = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    result = json.load(response)
                if result.get("code", 0) != 0:
                    raise ProviderError("FEISHU_API_ERROR", result.get("msg") or "unknown", detail={"code": result.get("code")})
                return result
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", "replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"msg": raw[:300]}
                last = ProviderError(
                    "FEISHU_HTTP_ERROR",
                    parsed.get("msg") or f"HTTP_{exc.code}",
                    detail={"http_status": exc.code, "code": parsed.get("code")},
                )
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                    raise last
            except urllib.error.URLError as exc:
                last = ProviderError("FEISHU_NETWORK_ERROR", str(exc.reason))
                if attempt >= retries:
                    raise last
            time.sleep(0.6 * (attempt + 1))
        assert last is not None
        raise last

    def _table_path(self, suffix: str = "") -> str:
        return (
            f"/bitable/v1/apps/{urllib.parse.quote(self.app_token, safe='')}"
            f"/tables/{urllib.parse.quote(self.table_id, safe='')}{suffix}"
        )

    def list_records(self) -> Iterable[dict[str, Any]]:
        page_token = None
        rows: list[dict] = []
        while True:
            result = self._json_request(
                "GET",
                self._table_path("/records"),
                query={"page_size": 500, "page_token": page_token},
            )
            data = result.get("data") or {}
            rows.extend(data.get("items") or data.get("records") or [])
            page_token = data.get("page_token")
            if not data.get("has_more") or not page_token:
                break
        return rows

    def get_record(self, record_id: str) -> dict[str, Any]:
        rid = urllib.parse.quote(record_id, safe="")
        result = self._json_request("GET", self._table_path(f"/records/{rid}"))
        record = (result.get("data") or {}).get("record")
        if not record:
            raise ProviderError("FEISHU_RECORD_MISSING", record_id)
        return record

    def list_field_names(self) -> list[str]:
        result = self._json_request("GET", self._table_path("/fields"), query={"page_size": 500})
        return [str(item.get("field_name")) for item in (result.get("data") or {}).get("items") or []]

    def download_attachment(self, file_token: str, target: Path) -> dict[str, Any]:
        if not file_token:
            raise ProviderError("FEISHU_FILE_TOKEN_MISSING")
        target.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            f"{self.api_root}/drive/v1/medias/{urllib.parse.quote(file_token, safe='')}/download",
            headers={"Authorization": f"Bearer {self.token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                with target.open("wb") as stream:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        stream.write(block)
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            raise ProviderError("FEISHU_DOWNLOAD_FAILED", f"HTTP_{exc.code}") from exc
        return {"ok": True, "bytes": target.stat().st_size, "content_type": content_type, "output": str(target)}

    @staticmethod
    def _multipart(fields: list[tuple[str, str]], *, file_name: str, file_bytes: bytes) -> tuple[bytes, str]:
        boundary = f"----Gvflow{int(time.time() * 1000)}"
        chunks: list[bytes] = []
        for name, value in fields:
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ])
        mime = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        return b"".join(chunks), boundary

    def _post_bytes(self, path: str, body: bytes, content_type: str, *, timeout: int = 300) -> dict:
        request = urllib.request.Request(
            f"{self.api_root}{path}",
            data=body,
            headers={"Content-Type": content_type, "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"msg": raw[:300]}
            raise ProviderError("FEISHU_UPLOAD_HTTP_ERROR", parsed.get("msg") or f"HTTP_{exc.code}") from exc
        if result.get("code", 0) != 0:
            raise ProviderError("FEISHU_UPLOAD_API_ERROR", result.get("msg") or "unknown", detail={"code": result.get("code")})
        return result

    def _upload_file(self, path: Path) -> str:
        size = path.stat().st_size
        if size <= UPLOAD_ALL_LIMIT:
            body, boundary = self._multipart(
                [
                    ("file_name", path.name),
                    ("parent_type", "bitable_image"),
                    ("parent_node", self.app_token),
                    ("size", str(size)),
                ],
                file_name=path.name,
                file_bytes=path.read_bytes(),
            )
            result = self._post_bytes("/drive/v1/medias/upload_all", body, f"multipart/form-data; boundary={boundary}")
            token = (result.get("data") or {}).get("file_token")
            if not token:
                raise ProviderError("FEISHU_UPLOAD_TOKEN_MISSING")
            return token

        prepared = self._json_request(
            "POST",
            "/drive/v1/medias/upload_prepare",
            payload={"file_name": path.name, "parent_type": "bitable_image", "parent_node": self.app_token, "size": size},
            timeout=300,
        )
        data = prepared.get("data") or {}
        upload_id = data.get("upload_id")
        block_size = int(data.get("block_size") or 4 * 1024 * 1024)
        block_num = int(data.get("block_num") or math.ceil(size / block_size))
        if not upload_id:
            raise ProviderError("FEISHU_UPLOAD_ID_MISSING")
        with path.open("rb") as stream:
            for sequence in range(block_num):
                blob = stream.read(block_size)
                body, boundary = self._multipart(
                    [("upload_id", upload_id), ("seq", str(sequence)), ("size", str(len(blob)))],
                    file_name=path.name,
                    file_bytes=blob,
                )
                self._post_bytes("/drive/v1/medias/upload_part", body, f"multipart/form-data; boundary={boundary}")
        finished = self._json_request(
            "POST",
            "/drive/v1/medias/upload_finish",
            payload={"upload_id": upload_id, "block_num": block_num},
            timeout=300,
        )
        token = (finished.get("data") or {}).get("file_token")
        if not token:
            raise ProviderError("FEISHU_UPLOAD_TOKEN_MISSING")
        return token

    def attach_files(
        self,
        record_id: str,
        field_name: str,
        paths: list[Path],
        *,
        replace_same_name: bool = False,
    ) -> dict[str, Any]:
        current = self.get_record(record_id)
        fields = current.get("fields") or {}
        existing = [item for item in fields.get(field_name, []) if isinstance(item, dict) and item.get("file_token")]
        new_names = {path.name for path in paths}
        replaced = []
        if replace_same_name:
            kept = []
            for item in existing:
                if item.get("name") in new_names:
                    replaced.append(item)
                else:
                    kept.append(item)
            existing = kept
        added = []
        for path in paths:
            if not path.is_file():
                raise ProviderError("LOCAL_ARTIFACT_MISSING", str(path))
            token = self._upload_file(path)
            added.append({"file_token": token, "name": path.name, "size": path.stat().st_size})
        payload = [{"file_token": item["file_token"], "name": item.get("name")} for item in existing]
        payload.extend({"file_token": item["file_token"], "name": item["name"]} for item in added)
        self.update_fields(record_id, {field_name: payload})
        readback = self.get_record(record_id)
        actual = [item for item in (readback.get("fields") or {}).get(field_name, []) if isinstance(item, dict)]
        actual_by_token = {item.get("file_token"): item for item in actual}
        mismatches = []
        for expected in added:
            item = actual_by_token.get(expected["file_token"])
            if not item or item.get("name") != expected["name"] or int(item.get("size") or -1) != expected["size"]:
                mismatches.append({"expected": expected, "actual": item})
        if mismatches:
            raise ProviderError("FEISHU_ATTACHMENT_READBACK_MISMATCH", detail=mismatches)
        return {"ok": True, "record_id": record_id, "added": added, "replaced": replaced, "attachments": actual}

    def update_fields(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        rid = urllib.parse.quote(record_id, safe="")
        self._json_request("PUT", self._table_path(f"/records/{rid}"), payload={"fields": fields})
        actual = self.get_record(record_id).get("fields") or {}
        def matches(expected: Any, observed: Any) -> bool:
            if isinstance(expected, list) and all(isinstance(item, dict) and item.get("file_token") for item in expected):
                if not isinstance(observed, list):
                    return False
                expected_tokens = [str(item.get("file_token")) for item in expected]
                observed_tokens = [str(item.get("file_token")) for item in observed if isinstance(item, dict) and item.get("file_token")]
                return expected_tokens == observed_tokens
            return observed == expected

        mismatches = {key: {"expected": expected, "actual": actual.get(key)} for key, expected in fields.items() if not matches(expected, actual.get(key))}
        if mismatches:
            raise ProviderError("FEISHU_FIELD_READBACK_MISMATCH", detail=mismatches)
        return {"ok": True, "verify": {"ok": True, "checked_fields": list(fields)}}

    def doctor(self) -> dict[str, Any]:
        names = set(self.list_field_names())
        mapping = self.config["fields"]
        required = {
            mapping["classification"],
            mapping["product"],
            mapping["published"],
            mapping["status"],
            mapping["note"],
            mapping["execution_log"],
        }
        if mapping.get("classification_fallback"):
            required.add(mapping["classification_fallback"])
        missing = sorted(required - names)
        available_sources = [name for name in mapping["source_priority"] if name in names]
        unavailable_sources = [name for name in mapping["source_priority"] if name not in names]
        return {
            "ok": not missing and bool(available_sources),
            "provider": "feishu",
            "table_id": self.table_id,
            "missing_fields": missing,
            "available_source_fields": available_sources,
            "unavailable_optional_source_fields": unavailable_sources,
        }
