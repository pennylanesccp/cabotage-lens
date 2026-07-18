from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from modules.costs.diesel_price_updater import ANP_URL, download_anp_file, process_anp_excel
from modules.costs.diesel_prices import DEFAULT_DIESEL_PRICES_CSV
from modules.costs.ship_fuel_prices import (
    DEFAULT_OUTPUT_TXT,
    apply_fx_brl,
    fetch_santos_prices,
    get_bunker_price,
    write_prices_txt,
)
from modules.infra.data_assets import (
    build_data_assets_client,
    load_data_assets_settings,
    resolve_data_asset_path,
)
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_DIR = _REPO_ROOT / ".cache" / "runtime_fuel_prices"
_RUNTIME_DIESEL_CSV = _RUNTIME_DIR / "latest_diesel_prices.csv"
_RUNTIME_BUNKER_TXT = _RUNTIME_DIR / "santos_bunker_brl.txt"
_ANP_WORKBOOK_OBJECT_PATH = "data/raw/road_data/semanal-estados-desde-2013.xlsx"
_DIESEL_PRICES_OBJECT_PATH = "data/processed/road_data/latest_diesel_prices.csv"
_ANP_WORKBOOK_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
_DIESEL_PRICES_CONTENT_TYPE = "text/csv; charset=utf-8"
_REFRESH_LOCK = threading.Lock()


@dataclass(frozen=True)
class FuelPriceRefreshResult:
    diesel_csv_path: Path
    bunker_price_brl_mt: float
    diesel_updated: bool
    bunker_updated: bool
    prices_changed: bool
    diesel_price_assets_archived: bool = False
    warnings: tuple[str, ...] = ()


def _active_diesel_path() -> Path:
    if _RUNTIME_DIESEL_CSV.is_file():
        return _RUNTIME_DIESEL_CSV.resolve()
    return resolve_data_asset_path(DEFAULT_DIESEL_PRICES_CSV).resolve()


def _active_bunker_path() -> Path | None:
    if _RUNTIME_BUNKER_TXT.is_file():
        return _RUNTIME_BUNKER_TXT.resolve()
    resolved = resolve_data_asset_path(Path(DEFAULT_OUTPUT_TXT)).resolve()
    return resolved if resolved.is_file() else None


def _files_differ(left: Path, right: Path) -> bool:
    if not left.is_file() or not right.is_file():
        return left.is_file() != right.is_file()
    return left.read_bytes() != right.read_bytes()


def _archive_anp_price_assets(
    workbook_path: Path,
    diesel_prices_path: Path,
    *,
    timeout_s: float,
) -> tuple[bool, str | None]:
    """Store the validated ANP workbook and normalized price table in Storage."""
    try:
        settings = load_data_assets_settings()
        if settings is None:
            return (
                False,
                "ANP price files were refreshed locally but could not be archived: "
                "Supabase Storage data assets are not configured.",
            )

        workbook_payload = workbook_path.read_bytes()
        diesel_prices_payload = diesel_prices_path.read_bytes()
        if not workbook_payload:
            return False, "ANP workbook archive skipped because the downloaded file is empty."
        if not diesel_prices_payload:
            return False, "ANP price-table archive skipped because the normalized CSV is empty."

        client = build_data_assets_client(settings)
        client.upload_bytes(
            bucket=settings.data_bucket,
            object_path=_ANP_WORKBOOK_OBJECT_PATH,
            payload=workbook_payload,
            content_type=_ANP_WORKBOOK_CONTENT_TYPE,
            upsert=True,
            timeout_s=timeout_s,
        )
        client.upload_bytes(
            bucket=settings.data_bucket,
            object_path=_DIESEL_PRICES_OBJECT_PATH,
            payload=diesel_prices_payload,
            content_type=_DIESEL_PRICES_CONTENT_TYPE,
            upsert=True,
            timeout_s=timeout_s,
        )
        _log.info(
            "Archived ANP price files to Supabase Storage bucket=%s workbook=%s workbook_bytes=%d "
            "prices=%s prices_bytes=%d.",
            settings.data_bucket,
            _ANP_WORKBOOK_OBJECT_PATH,
            len(workbook_payload),
            _DIESEL_PRICES_OBJECT_PATH,
            len(diesel_prices_payload),
        )
        return True, None
    except Exception as exc:
        return False, f"ANP price-file archive failed; local diesel prices remain active ({exc})."


def _refresh_diesel(
    baseline_path: Path,
    *,
    timeout_s: float,
) -> tuple[Path, bool, bool, bool, str | None]:
    token = uuid.uuid4().hex
    raw_tmp = _RUNTIME_DIR / f"anp-{token}.xlsx"
    diesel_tmp = _RUNTIME_DIR / f"diesel-{token}.csv"
    try:
        if not download_anp_file(ANP_URL, raw_tmp, timeout=timeout_s):
            return baseline_path, False, False, False, "ANP diesel refresh failed; using the previous price table."
        process_anp_excel(raw_tmp, diesel_tmp)
        if not diesel_tmp.is_file() or diesel_tmp.stat().st_size <= 0:
            return (
                baseline_path,
                False,
                False,
                False,
                "ANP diesel refresh produced no usable price table; using the previous table.",
            )
        changed = _files_differ(diesel_tmp, baseline_path)
        diesel_tmp.replace(_RUNTIME_DIESEL_CSV)
        archived, archive_warning = _archive_anp_price_assets(
            raw_tmp,
            _RUNTIME_DIESEL_CSV,
            timeout_s=timeout_s,
        )
        return _RUNTIME_DIESEL_CSV.resolve(), True, changed, archived, archive_warning
    except Exception as exc:
        return baseline_path, False, False, False, f"ANP diesel refresh failed; using the previous price table ({exc})."
    finally:
        for path in (raw_tmp, diesel_tmp):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def _refresh_bunker(
    baseline_price: float,
    *,
    timeout_s: float,
) -> tuple[float, bool, bool, str | None]:
    bunker_tmp = _RUNTIME_DIR / f"bunker-{uuid.uuid4().hex}.txt"
    try:
        prices_brl = apply_fx_brl(fetch_santos_prices(timeout=timeout_s))
        write_prices_txt(prices_brl, output_path=str(bunker_tmp), append=False)
        bunker_price = float(prices_brl["vlsfo_brl_per_mt"])
        bunker_tmp.replace(_RUNTIME_BUNKER_TXT)
        changed = abs(bunker_price - baseline_price) > 0.005
        return bunker_price, True, changed, None
    except Exception as exc:
        return baseline_price, False, False, f"Ship & Bunker refresh failed; using the previous bunker price ({exc})."
    finally:
        try:
            bunker_tmp.unlink(missing_ok=True)
        except OSError:
            pass


def refresh_fuel_prices(*, timeout_s: float = 30.0) -> FuelPriceRefreshResult:
    """Always attempt live diesel and bunker refreshes, with local fallback."""
    with _REFRESH_LOCK:
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        baseline_diesel_path = _active_diesel_path()
        baseline_bunker_path = _active_bunker_path()
        baseline_bunker_price = get_bunker_price(
            price_path=baseline_bunker_path,
            default_price_brl_mt=3500.0,
        )

        _log.info("Refreshing live fuel prices before evaluation.")
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="fuel-price-refresh") as executor:
            diesel_future = executor.submit(_refresh_diesel, baseline_diesel_path, timeout_s=timeout_s)
            bunker_future = executor.submit(_refresh_bunker, baseline_bunker_price, timeout_s=timeout_s)
            (
                diesel_path,
                diesel_updated,
                diesel_changed,
                diesel_price_assets_archived,
                diesel_warning,
            ) = diesel_future.result()
            bunker_price, bunker_updated, bunker_changed, bunker_warning = bunker_future.result()

        warnings = [warning for warning in (diesel_warning, bunker_warning) if warning]

        for warning in warnings:
            _log.warning(warning)
        _log.info(
            (
                "Fuel price refresh complete diesel_updated=%s diesel_price_assets_archived=%s "
                "bunker_updated=%s prices_changed=%s diesel_csv=%s bunker_price_brl_mt=%.2f"
            ),
            diesel_updated,
            diesel_price_assets_archived,
            bunker_updated,
            bool(diesel_changed or bunker_changed),
            diesel_path,
            bunker_price,
        )
        return FuelPriceRefreshResult(
            diesel_csv_path=diesel_path,
            bunker_price_brl_mt=float(bunker_price),
            diesel_updated=diesel_updated,
            bunker_updated=bunker_updated,
            prices_changed=bool(diesel_changed or bunker_changed),
            diesel_price_assets_archived=diesel_price_assets_archived,
            warnings=tuple(warnings),
        )
