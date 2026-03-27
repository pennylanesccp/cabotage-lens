from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional
from urllib.parse import quote

import requests

from modules.core.secrets import get_secret


def _clean_secret(name: str) -> Optional[str]:
    value = get_secret(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _infer_base_url() -> Optional[str]:
    explicit = _clean_secret("SUPABASE_URL")
    if explicit:
        return explicit.rstrip("/")

    project_ref = _clean_secret("SUPABASE_PROJECT_REF")
    if not project_ref:
        return None
    return f"https://{project_ref}.supabase.co"


@dataclass(frozen=True)
class SupabaseStorageSettings:
    base_url: str
    api_key: str
    logs_bucket: str


def load_supabase_storage_settings() -> SupabaseStorageSettings:
    base_url = _infer_base_url()
    api_key = _clean_secret("SUPABASE_SERVICE_ROLE_KEY") or _clean_secret("SUPABASE_KEY")
    logs_bucket = _clean_secret("SUPABASE_STORAGE_LOGS_BUCKET")

    if not base_url:
        raise RuntimeError("Supabase Storage archival requires SUPABASE_URL or SUPABASE_PROJECT_REF.")
    if not api_key:
        raise RuntimeError("Supabase Storage archival requires SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY.")
    if not logs_bucket:
        raise RuntimeError("Supabase Storage archival requires SUPABASE_STORAGE_LOGS_BUCKET.")

    return SupabaseStorageSettings(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        logs_bucket=logs_bucket,
    )


def build_log_archive_object_path(
    *,
    environment: str,
    run_id: str,
    now: Optional[datetime] = None,
    suffix: str = ".jsonl.gz",
) -> str:
    timestamp = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    env_segment = str(environment or "local").strip().lower() or "local"
    safe_run_id = str(run_id or "").strip() or timestamp.strftime("%Y%m%d%H%M%S")
    return (
        f"logs/{env_segment}/"
        f"{timestamp:%Y}/{timestamp:%m}/{timestamp:%d}/"
        f"{safe_run_id}{suffix}"
    )


class SupabaseStorageClient:
    def __init__(self, settings: Optional[SupabaseStorageSettings] = None) -> None:
        self._settings = settings or load_supabase_storage_settings()

    @property
    def settings(self) -> SupabaseStorageSettings:
        return self._settings

    def _headers(self, *, content_type: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.api_key}",
            "apikey": self._settings.api_key,
            "Content-Type": content_type,
        }

    def _object_url(self, *, bucket: str, object_path: str) -> str:
        quoted_path = quote(str(object_path).lstrip("/"), safe="/")
        return f"{self._settings.base_url}/storage/v1/object/{bucket}/{quoted_path}"

    def upload_bytes(
        self,
        *,
        object_path: str,
        payload: bytes,
        content_type: str,
        bucket: str | None = None,
        upsert: bool = True,
        timeout_s: float = 30.0,
    ) -> None:
        target_bucket = str(bucket or self._settings.logs_bucket).strip()
        if not target_bucket:
            raise RuntimeError("Supabase Storage upload requires a target bucket.")
        url = self._object_url(bucket=target_bucket, object_path=object_path)
        response = requests.post(
            url,
            headers=self._headers(content_type=content_type) | {"x-upsert": "true" if upsert else "false"},
            data=payload,
            timeout=timeout_s,
        )
        response.raise_for_status()

    def download_bytes(
        self,
        *,
        bucket: str,
        object_path: str,
        timeout_s: float = 30.0,
    ) -> bytes:
        target_bucket = str(bucket).strip()
        if not target_bucket:
            raise RuntimeError("Supabase Storage download requires a target bucket.")

        url = self._object_url(bucket=target_bucket, object_path=object_path)
        response = requests.get(
            url,
            headers=self._headers(content_type="application/octet-stream"),
            timeout=timeout_s,
        )
        response.raise_for_status()
        return response.content

    def list_objects(
        self,
        *,
        bucket: str,
        prefix: str = "",
        limit: int = 1_000,
        timeout_s: float = 30.0,
    ) -> list[dict[str, Any]]:
        target_bucket = str(bucket).strip()
        if not target_bucket:
            raise RuntimeError("Supabase Storage list requires a target bucket.")

        url = f"{self._settings.base_url}/storage/v1/object/list/{target_bucket}"
        response = requests.post(
            url,
            headers=self._headers(content_type="application/json"),
            json={
                "prefix": str(prefix or "").strip().lstrip("/"),
                "limit": int(limit),
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"},
            },
            timeout=timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Supabase Storage list response must be a list.")
        return [item for item in payload if isinstance(item, dict)]
