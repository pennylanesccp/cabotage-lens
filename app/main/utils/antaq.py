from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable

from modules.cabotage.antaq_refresh import DEFAULT_BUCKET, refresh_antaq_pipeline
from modules.infra.data_assets import cache_data_asset_from_local, load_data_assets_settings
from modules.infra.log_manager import get_logger
from modules.multimodal.builder import invalidate_routing_asset_caches

_log = get_logger(__name__)

DEFAULT_ANTAQ_REFRESH_START_YEAR = 2020
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

    summary = refresh_antaq_pipeline(
        years=years,
        ensure_db_schema=True,
        load_db=True,
        sync_bucket=sync_bucket,
        bucket=bucket,
        progress_callback=progress_callback,
    )
    _seed_local_refresh_outputs_into_cache(summary)
    invalidate_routing_asset_caches()
    return summary


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
