from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable

from modules.cabotage.antaq_refresh import (
    DEFAULT_BUCKET,
    DEFAULT_RAW_DIR,
    DEFAULT_REQUIRED_TABLES,
    refresh_antaq_pipeline,
)
from modules.infra.data_assets import cache_data_asset_from_local, load_data_assets_settings
from modules.infra.log_manager import get_logger
from modules.multimodal.builder import invalidate_routing_asset_caches

_log = get_logger(__name__)

DEFAULT_ANTAQ_REFRESH_START_YEAR = 2020
ANTAQ_REFRESH_UNAVAILABLE_MESSAGE = (
    "ANTAQ automatic refresh is unavailable right now. "
    "The app will continue using local/cache data when available."
)
_ANTAQ_PORTAL_FAILURE_TEXT = "Failed to reach the ANTAQ download portal."
_ProgressCallback = Callable[[dict[str, Any]], None]


def antaq_refresh_years(*, start_year: int = DEFAULT_ANTAQ_REFRESH_START_YEAR) -> list[str]:
    current_year = date.today().year
    return [str(year) for year in range(int(start_year), int(current_year) + 1)]


def antaq_refresh_label(*, start_year: int = DEFAULT_ANTAQ_REFRESH_START_YEAR) -> str:
    years = antaq_refresh_years(start_year=start_year)
    return f"Refresh ANTAQ data before run ({years[0]}-{years[-1]})"


def run_antaq_refresh_for_app(
    *,
    progress_callback: _ProgressCallback | None = None,
    start_year: int = DEFAULT_ANTAQ_REFRESH_START_YEAR,
) -> dict[str, Any]:
    years = antaq_refresh_years(start_year=start_year)
    data_asset_settings = load_data_assets_settings()
    sync_bucket = data_asset_settings is not None
    bucket = data_asset_settings.data_bucket if data_asset_settings is not None else DEFAULT_BUCKET

    if not sync_bucket:
        _log.warning(
            "ANTAQ refresh will skip bucket sync because Supabase Storage data assets are not configured."
        )

    pipeline_kwargs = {
        "years": years,
        "ensure_db_schema": True,
        "load_db": True,
        "sync_bucket": sync_bucket,
        "bucket": bucket,
        "progress_callback": progress_callback,
    }
    try:
        summary = refresh_antaq_pipeline(**pipeline_kwargs)
    except Exception as exc:
        if not _is_antaq_portal_failure(exc):
            raise
        _log.exception(
            "ANTAQ portal refresh failed for app runtime; checking for local raw TXT fallback."
        )
        if _has_required_raw_txt_files(years):
            _log.warning("Retrying ANTAQ refresh with skip_download=True using local raw TXT files.")
            summary = refresh_antaq_pipeline(**pipeline_kwargs, skip_download=True)
            summary["app_refresh_status"] = {
                "ok": True,
                "used_local_raw_fallback": True,
                "message": (
                    "ANTAQ portal refresh is unavailable; refreshed using local raw TXT files."
                ),
            }
        else:
            _log.warning(
                "ANTAQ portal refresh unavailable and required local raw TXT files are absent; "
                "continuing with existing local/cache data when available."
            )
            return _antaq_refresh_unavailable_summary(years=years, exc=exc)
    else:
        summary["app_refresh_status"] = {"ok": True, "used_local_raw_fallback": False}
    _seed_local_refresh_outputs_into_cache(summary)
    invalidate_routing_asset_caches()
    return summary


def _is_antaq_portal_failure(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if _ANTAQ_PORTAL_FAILURE_TEXT in str(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def _has_required_raw_txt_files(years: list[str], raw_dir: Path | str | None = None) -> bool:
    raw_root = Path(DEFAULT_RAW_DIR if raw_dir is None else raw_dir)
    return all((raw_root / f"{year}{table}.txt").exists() for year in years for table in DEFAULT_REQUIRED_TABLES)


def _antaq_refresh_unavailable_summary(*, years: list[str], exc: BaseException) -> dict[str, Any]:
    return {
        "years": years,
        "download": {
            "files_requested": len(years) * len(DEFAULT_REQUIRED_TABLES),
            "files_downloaded": 0,
            "skipped": True,
            "results": [],
        },
        "app_refresh_status": {
            "ok": False,
            "reason": "portal_unavailable_no_local_raw",
            "message": ANTAQ_REFRESH_UNAVAILABLE_MESSAGE,
            "error": str(exc),
        },
    }


def _seed_local_refresh_outputs_into_cache(summary: dict[str, Any]) -> None:
    cached_targets: list[Path] = []

    voyages_output = str((summary.get("voyages_build") or {}).get("output_json") or "").strip()
    if voyages_output:
        cached_targets.append(Path(voyages_output))

    materialized_outputs = (summary.get("materialize") or {}).get("outputs") or {}
    if isinstance(materialized_outputs, dict):
        for value in materialized_outputs.values():
            text = str(value or "").strip()
            if text:
                cached_targets.append(Path(text))

    sea_matrix_output = str((summary.get("sea_matrix") or {}).get("output_json") or "").strip()
    if sea_matrix_output:
        cached_targets.append(Path(sea_matrix_output))

    for path in cached_targets:
        try:
            cache_path = cache_data_asset_from_local(path)
        except Exception as exc:
            _log.debug("Failed to seed refreshed asset into local Supabase cache path=%s error=%s", path, exc)
            continue
        if cache_path is not None:
            _log.info("Seeded refreshed data asset into local cache source=%s cache=%s", path, cache_path)
