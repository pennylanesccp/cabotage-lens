from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from modules.cabotage.antaq_voyage_tables import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_VOYAGES_JSON_PATH,
    load_observed_voyages_payload,
    materialize_voyage_tables,
    upsert_tables_to_db,
    write_tables_to_disk,
)
from modules.cabotage.sea_matrix_efficiency import (
    DEFAULT_MRV_JSON_PATH,
    DEFAULT_SEA_MATRIX_PATH,
    enrich_sea_matrix_with_efficiency,
    write_enriched_sea_matrix,
)
from modules.infra.data_bucket_sync import build_upload_plan, execute_upload_plan
from modules.infra.db.core import connection_target_summary, db_session
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = Path("data/raw/cabotage_data")
DEFAULT_DOWNLOAD_PAGE_URL = "https://web3.antaq.gov.br/ea/sense/download.html"
DEFAULT_TXT_BASE_URL = "https://web3.antaq.gov.br/ea/txt/"
DEFAULT_BUCKET = "cabotage-lens"
DEFAULT_REQUIRED_TABLES = ("Atracacao", "Carga", "TemposAtracacao")
DEFAULT_DB_MIGRATION_PATH = Path("supabase/migrations/20260327_000006_antaq_voyage_tables.sql")
_URL_REGEX = re.compile(r"""(?P<url>(?:https?:)?//[^\s"'<>]+|/[^\s"'<>]+|[A-Za-z0-9._/\-]+?\.(?:zip|txt))""")
_ZIP_MAGIC = b"PK\x03\x04"


@dataclass(frozen=True)
class AntaqDownloadResult:
    year: str
    table: str
    source_url: str
    target_path: str
    bytes_written: int
    archive_member: str | None
    content_kind: str
    skipped_existing: bool


def refresh_antaq_pipeline(
    *,
    years: Iterable[str],
    raw_dir: Path | str = DEFAULT_RAW_DIR,
    voyages_output_path: Path | str = DEFAULT_VOYAGES_JSON_PATH,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    sea_matrix_path: Path | str = DEFAULT_SEA_MATRIX_PATH,
    mrv_json_path: Path | str = DEFAULT_MRV_JSON_PATH,
    include_raw_jsonl: bool = False,
    max_gap_hours: float = 240.0,
    ensure_db_schema: bool = False,
    load_db: bool = False,
    sync_bucket: bool = False,
    bucket: str = DEFAULT_BUCKET,
    max_file_mb: float = 50.0,
    download_page_url: str = DEFAULT_DOWNLOAD_PAGE_URL,
    txt_base_url: str = DEFAULT_TXT_BASE_URL,
    force_download: bool = False,
    skip_download: bool = False,
    keep_all_matrix_pairs: bool = False,
    keep_unmatched_pairs: bool = False,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    ordered_years = _normalize_years(years)
    raw_root = Path(raw_dir).resolve()
    voyages_output = Path(voyages_output_path).resolve()
    tabular_output = Path(output_dir).resolve()
    sea_matrix_output = Path(sea_matrix_path).resolve()
    mrv_path = Path(mrv_json_path).resolve()

    download_results: list[AntaqDownloadResult] = []
    if not skip_download:
        download_results = download_antaq_txt_tables(
            years=ordered_years,
            raw_dir=raw_root,
            required_tables=DEFAULT_REQUIRED_TABLES,
            download_page_url=download_page_url,
            txt_base_url=txt_base_url,
            force=force_download,
            timeout_s=timeout_s,
        )

    build_summary = run_antaq_voyage_builder(
        years=ordered_years,
        output_path=voyages_output,
        max_gap_hours=max_gap_hours,
    )

    db_schema_summary: dict[str, Any] | None = None
    if ensure_db_schema:
        db_schema_summary = ensure_antaq_voyage_schema()

    source_path, payload = load_observed_voyages_payload(voyages_output)
    tables = materialize_voyage_tables(payload, source_path=source_path)
    materialized_outputs = write_tables_to_disk(
        tables,
        output_dir=tabular_output,
        include_raw_jsonl=bool(include_raw_jsonl),
    )

    materialize_summary: dict[str, Any] = {
        "source_json": str(source_path),
        "output_dir": str(tabular_output),
        "voyages_rows": len(tables.voyages),
        "stops_rows": len(tables.stops),
        "stop_calls_rows": len(tables.stop_calls),
        "raw_rows": len(tables.raw_rows),
        "outputs": materialized_outputs,
    }
    if load_db:
        with db_session() as conn:
            materialize_summary["db_target"] = connection_target_summary()
            materialize_summary["db_upsert"] = upsert_tables_to_db(conn, tables)

    enriched_payload, sea_matrix_summary = enrich_sea_matrix_with_efficiency(
        sea_matrix_path=sea_matrix_output,
        voyages_csv_path=Path(materialized_outputs["voyages_csv"]),
        stops_csv_path=Path(materialized_outputs["stops_csv"]),
        mrv_json_path=mrv_path,
        possible_pairs_only=not bool(keep_all_matrix_pairs),
        matched_pairs_only=not bool(keep_unmatched_pairs),
        prefer_local_voyage_inputs=True,
    )
    resolved_sea_matrix_path = write_enriched_sea_matrix(
        enriched_payload,
        output_path=sea_matrix_output,
    )

    bucket_summary: dict[str, Any] | None = None
    if sync_bucket:
        plan = build_upload_plan(
            data_root=(_REPO_ROOT / "data").resolve(),
            max_file_size_bytes=int(max_file_mb * 1024 * 1024),
        )
        bucket_summary = execute_upload_plan(
            plan=plan,
            bucket=bucket,
            dry_run=False,
        )

    return {
        "years": ordered_years,
        "download": {
            "files_requested": len(ordered_years) * len(DEFAULT_REQUIRED_TABLES),
            "files_downloaded": len(download_results),
            "skipped": bool(skip_download),
            "results": [asdict(item) for item in download_results],
        },
        "voyages_build": build_summary,
        "db_schema": db_schema_summary,
        "materialize": materialize_summary,
        "sea_matrix": {
            "output_json": str(resolved_sea_matrix_path),
            **sea_matrix_summary,
        },
        "bucket_sync": bucket_summary,
    }


def download_antaq_txt_tables(
    *,
    years: Iterable[str],
    raw_dir: Path,
    required_tables: Iterable[str],
    download_page_url: str = DEFAULT_DOWNLOAD_PAGE_URL,
    txt_base_url: str = DEFAULT_TXT_BASE_URL,
    force: bool = False,
    timeout_s: float = 120.0,
) -> list[AntaqDownloadResult]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    try:
        portal_sources = _load_portal_sources(
            session=session,
            download_page_url=download_page_url,
            timeout_s=timeout_s,
        )
        results: list[AntaqDownloadResult] = []
        for year in _normalize_years(years):
            for table in required_tables:
                results.append(
                    _download_year_table(
                        session=session,
                        portal_sources=portal_sources,
                        year=year,
                        table=table,
                        raw_dir=raw_dir,
                        txt_base_url=txt_base_url,
                        force=force,
                        timeout_s=timeout_s,
                    )
                )
        return results
    finally:
        session.close()


def run_antaq_voyage_builder(
    *,
    years: Iterable[str],
    output_path: Path,
    max_gap_hours: float,
) -> dict[str, Any]:
    script_path = (_REPO_ROOT / "calcs" / "build_antaq_cabotage_voyages.ps1").resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Missing ANTAQ voyage builder script: {script_path}")

    ps_executable = _resolve_powershell_executable()
    command = [
        ps_executable,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-OutputPath",
        str(output_path),
        "-MaxGapHours",
        str(max_gap_hours),
        "-Years",
        *list(_normalize_years(years)),
    ]
    _log.info("Running ANTAQ voyage builder: %s", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        raise RuntimeError(
            "ANTAQ voyage builder failed with exit code "
            f"{completed.returncode}: {stderr or stdout or 'no output'}"
        )
    if not output_path.exists():
        raise RuntimeError(f"ANTAQ voyage builder did not create expected JSON: {output_path}")

    _, payload = load_observed_voyages_payload(output_path)
    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    return {
        "output_json": str(output_path),
        "stdout": [line for line in stdout.splitlines() if line.strip()],
        "stderr": [line for line in stderr.splitlines() if line.strip()],
        "generated_at": payload.get("generated_at"),
        "voyages": stats.get("voyages"),
        "unique_imos": stats.get("unique_imos"),
        "joined_calls": stats.get("joined_calls"),
        "source_files": payload.get("source_files"),
    }


def ensure_antaq_voyage_schema(
    *,
    migration_path: Path | str = DEFAULT_DB_MIGRATION_PATH,
) -> dict[str, Any]:
    resolved = Path(migration_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Missing migration file: {resolved}")

    sql = resolved.read_text(encoding="utf-8")
    with db_session() as conn:
        conn.execute(sql)
    return {
        "migration_path": str(resolved),
        "db_target": connection_target_summary(),
        "applied": True,
    }


def _normalize_years(years: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in years:
        year = str(raw).strip()
        if not re.fullmatch(r"\d{4}", year):
            raise ValueError(f"Invalid ANTAQ year: {raw!r}")
        if year in seen:
            continue
        ordered.append(year)
        seen.add(year)
    if not ordered:
        raise ValueError("At least one ANTAQ year must be provided.")
    return ordered


def _load_portal_sources(
    *,
    session: requests.Session,
    download_page_url: str,
    timeout_s: float,
) -> list[tuple[str, str]]:
    try:
        response = session.get(download_page_url, timeout=timeout_s)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "Failed to reach the ANTAQ download portal. "
            "Check internet access or rerun with --skip-download if the raw TXT files are already present locally."
        ) from exc
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    sources: list[tuple[str, str]] = [(download_page_url, html)]
    for script_tag in soup.find_all("script"):
        src = str(script_tag.get("src") or "").strip()
        if not src:
            inline = script_tag.string or script_tag.get_text() or ""
            if inline.strip():
                sources.append((download_page_url, inline))
            continue
        url = urljoin(download_page_url, src)
        try:
            script_response = session.get(url, timeout=timeout_s)
            script_response.raise_for_status()
        except requests.RequestException as exc:
            _log.warning("Failed to fetch ANTAQ script asset %s: %s", url, exc)
            continue
        sources.append((url, script_response.text))
    return sources


def _download_year_table(
    *,
    session: requests.Session,
    portal_sources: list[tuple[str, str]],
    year: str,
    table: str,
    raw_dir: Path,
    txt_base_url: str,
    force: bool,
    timeout_s: float,
) -> AntaqDownloadResult:
    target_path = raw_dir / f"{year}{table}.txt"
    if target_path.exists() and not force:
        return AntaqDownloadResult(
            year=year,
            table=table,
            source_url="",
            target_path=str(target_path),
            bytes_written=target_path.stat().st_size,
            archive_member=None,
            content_kind="existing",
            skipped_existing=True,
        )

    candidates = _candidate_urls(
        portal_sources=portal_sources,
        year=year,
        table=table,
        txt_base_url=txt_base_url,
    )
    attempted: list[str] = []
    for url in candidates:
        attempted.append(url)
        try:
            result = _download_candidate_url(
                session=session,
                url=url,
                year=year,
                table=table,
                target_path=target_path,
                timeout_s=timeout_s,
            )
        except requests.RequestException as exc:
            _log.debug("ANTAQ candidate failed %s: %s", url, exc)
            continue
        if result is not None:
            return result

    raise RuntimeError(
        f"Could not resolve ANTAQ download for {year}{table}. Attempted URLs: "
        + ", ".join(attempted)
    )


def _candidate_urls(
    *,
    portal_sources: list[tuple[str, str]],
    year: str,
    table: str,
    txt_base_url: str,
) -> list[str]:
    normalized_table = table.lower()
    discovered: list[str] = []
    seen: set[str] = set()

    for base_url, content in portal_sources:
        for match in _URL_REGEX.finditer(content):
            raw = match.group("url").strip().strip("\"'();,")
            if not raw:
                continue
            lowered = raw.lower()
            if normalized_table not in lowered:
                continue
            if year not in lowered and "{" not in raw and "%s" not in raw.lower():
                continue
            if not lowered.endswith((".zip", ".txt")):
                continue
            absolute = urljoin(base_url, raw)
            if absolute not in seen:
                discovered.append(absolute)
                seen.add(absolute)

    fallback_names = [
        f"{year}{table}.zip",
        f"{year}{table}.txt",
    ]
    for name in fallback_names:
        url = urljoin(txt_base_url, name)
        if url not in seen:
            discovered.append(url)
            seen.add(url)

    return discovered


def _download_candidate_url(
    *,
    session: requests.Session,
    url: str,
    year: str,
    table: str,
    target_path: Path,
    timeout_s: float,
) -> AntaqDownloadResult | None:
    response = session.get(url, stream=True, timeout=timeout_s)
    if response.status_code >= 400:
        response.close()
        return None

    with tempfile.NamedTemporaryFile(delete=False) as handle:
        temp_path = Path(handle.name)
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    response.close()

    try:
        bytes_written = temp_path.stat().st_size
        if bytes_written <= 0:
            return None

        content_kind = _detect_content_kind(url, response.headers.get("Content-Type"), temp_path)
        if content_kind == "html":
            return None
        archive_member: str | None = None
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if content_kind == "zip":
            archive_member = _extract_matching_txt_from_zip(
                archive_path=temp_path,
                year=year,
                table=table,
                target_path=target_path,
            )
            bytes_written = target_path.stat().st_size
        else:
            shutil.move(str(temp_path), str(target_path))
            temp_path = Path()
            bytes_written = target_path.stat().st_size

        return AntaqDownloadResult(
            year=year,
            table=table,
            source_url=response.url or url,
            target_path=str(target_path),
            bytes_written=bytes_written,
            archive_member=archive_member,
            content_kind=content_kind,
            skipped_existing=False,
        )
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _detect_content_kind(url: str, content_type: str | None, payload_path: Path) -> str:
    lowered_url = url.lower()
    lowered_type = (content_type or "").lower()
    if "text/html" in lowered_type or "application/xhtml" in lowered_type:
        return "html"
    if lowered_url.endswith(".zip") or "zip" in lowered_type:
        return "zip"
    with payload_path.open("rb") as handle:
        probe = handle.read(512)
    lowered_probe = probe.lstrip().lower()
    if lowered_probe.startswith(b"<!doctype html") or lowered_probe.startswith(b"<html"):
        return "html"
    magic = probe[:4]
    if magic == _ZIP_MAGIC:
        return "zip"
    return "txt"


def _extract_matching_txt_from_zip(
    *,
    archive_path: Path,
    year: str,
    table: str,
    target_path: Path,
) -> str:
    desired_name = f"{year}{table}.txt".lower()
    with zipfile.ZipFile(archive_path) as zf:
        members = [name for name in zf.namelist() if not name.endswith("/")]
        txt_members = [name for name in members if name.lower().endswith(".txt")]
        preferred = [name for name in txt_members if name.lower().endswith(desired_name)]
        candidates = preferred or txt_members
        if len(candidates) == 1:
            chosen = candidates[0]
        else:
            contains_table = [name for name in candidates if table.lower() in Path(name).name.lower()]
            if len(contains_table) == 1:
                chosen = contains_table[0]
            elif contains_table:
                chosen = sorted(contains_table, key=lambda item: len(item))[0]
            elif candidates:
                chosen = sorted(candidates, key=lambda item: len(item))[0]
            else:
                raise RuntimeError(f"ZIP archive has no TXT payload for {year}{table}: {archive_path}")
        with zf.open(chosen) as source, target_path.open("wb") as target:
            shutil.copyfileobj(source, target)
    return chosen


def _resolve_powershell_executable() -> str:
    for candidate in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("PowerShell executable not found. Install PowerShell or run the pipeline on Windows.")
