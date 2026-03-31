from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from modules.core.secrets import get_secret
from modules.infra.supabase_storage import SupabaseStorageClient, SupabaseStorageSettings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CACHE_DIR = _REPO_ROOT / ".cache" / "supabase_data"


def _clean_secret(name: str) -> Optional[str]:
    value = get_secret(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _boolish(value: object, default: bool) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class DataAssetsSettings:
    base_url: str
    api_key: str
    data_bucket: str
    prefer_remote: bool
    cache_dir: Path


def load_data_assets_settings() -> Optional[DataAssetsSettings]:
    project_ref = _clean_secret("SUPABASE_PROJECT_REF")
    base_url = _clean_secret("SUPABASE_URL") or (f"https://{project_ref}.supabase.co" if project_ref else None)
    api_key = _clean_secret("SUPABASE_SERVICE_ROLE_KEY") or _clean_secret("SUPABASE_KEY")
    data_bucket = _clean_secret("SUPABASE_STORAGE_DATA_BUCKET") or "cabotage-lens"
    enabled = _boolish(get_secret("SUPABASE_STORAGE_DATA_ENABLED"), default=bool(base_url and api_key))
    prefer_remote = _boolish(get_secret("SUPABASE_STORAGE_DATA_PREFER_REMOTE"), default=True)
    cache_dir_raw = _clean_secret("SUPABASE_STORAGE_DATA_CACHE_DIR")
    cache_dir = Path(cache_dir_raw) if cache_dir_raw else _DEFAULT_CACHE_DIR

    if not enabled:
        return None
    if not base_url or not api_key or not data_bucket:
        return None

    return DataAssetsSettings(
        base_url=base_url,
        api_key=api_key,
        data_bucket=data_bucket,
        prefer_remote=prefer_remote,
        cache_dir=cache_dir,
    )


def build_data_assets_client(settings: DataAssetsSettings | None = None) -> SupabaseStorageClient:
    effective = settings or load_data_assets_settings()
    if effective is None:
        raise RuntimeError(
            "Supabase Storage data assets are not configured. "
            "Set SUPABASE_STORAGE_DATA_ENABLED=true plus SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY, "
            "and either SUPABASE_URL or SUPABASE_PROJECT_REF."
        )

    return SupabaseStorageClient(
        settings=SupabaseStorageSettings(
            base_url=effective.base_url,
            api_key=effective.api_key,
            logs_bucket=effective.data_bucket,
        )
    )


def _repo_relative_data_path(candidate: Path | str) -> Optional[Path]:
    path = Path(candidate)
    if path.is_absolute():
        try:
            relative = path.resolve().relative_to(_REPO_ROOT.resolve())
        except Exception:
            return None
    else:
        relative = path

    if not relative.parts:
        return None
    if relative.parts[0] != "data":
        return None
    return relative


def _local_repo_path(relative_path: Path) -> Path:
    return (_REPO_ROOT / relative_path).resolve()


def _cache_path(settings: DataAssetsSettings, relative_path: Path) -> Path:
    return (settings.cache_dir / relative_path).resolve()


def cache_data_asset_from_local(candidate: Path | str) -> Path | None:
    relative = _repo_relative_data_path(candidate)
    path = Path(candidate)

    if relative is None:
        return None

    local_path = _local_repo_path(relative)
    if not local_path.exists():
        raise FileNotFoundError(f"Local data asset not found: {local_path}")

    settings = load_data_assets_settings()
    if settings is None:
        return None

    cache_path = _cache_path(settings, relative)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(local_path.read_bytes())
    return cache_path


def _is_not_found(exc: requests.HTTPError) -> bool:
    response = getattr(exc, "response", None)
    return bool(response is not None and response.status_code == 404)


def _download_remote_asset_bytes(
    *,
    client: SupabaseStorageClient,
    settings: DataAssetsSettings,
    relative_path: Path,
) -> bytes:
    object_path = relative_path.as_posix()

    try:
        return client.download_bytes(
            bucket=settings.data_bucket,
            object_path=object_path,
        )
    except requests.HTTPError as exc:
        if not _is_not_found(exc):
            raise

    manifest_object_path = f"{object_path}.manifest.json"
    manifest_payload = client.download_bytes(
        bucket=settings.data_bucket,
        object_path=manifest_object_path,
    )
    manifest = json.loads(manifest_payload.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid asset manifest for '{manifest_object_path}'.")

    storage_object_path = str(manifest.get("storage_object_path") or "").strip()
    if not storage_object_path:
        raise ValueError(f"Asset manifest '{manifest_object_path}' is missing storage_object_path.")

    payload = client.download_bytes(
        bucket=settings.data_bucket,
        object_path=storage_object_path,
    )
    if bool(manifest.get("compressed")):
        return gzip.decompress(payload)
    return payload


def resolve_data_asset_path(
    candidate: Path | str,
    *,
    force_refresh: bool = False,
) -> Path:
    relative = _repo_relative_data_path(candidate)
    path = Path(candidate)

    if relative is None:
        return path.resolve() if path.exists() else path

    local_path = _local_repo_path(relative)
    settings = load_data_assets_settings()

    if settings is None:
        return local_path

    remote_cache_path = _cache_path(settings, relative)
    if not force_refresh and not settings.prefer_remote and local_path.exists():
        return local_path
    if not force_refresh and remote_cache_path.exists():
        return remote_cache_path

    client = build_data_assets_client(settings)
    try:
        payload = _download_remote_asset_bytes(
            client=client,
            settings=settings,
            relative_path=relative,
        )
    except requests.RequestException:
        if local_path.exists():
            return local_path
        raise

    remote_cache_path.parent.mkdir(parents=True, exist_ok=True)
    remote_cache_path.write_bytes(payload)
    return remote_cache_path
