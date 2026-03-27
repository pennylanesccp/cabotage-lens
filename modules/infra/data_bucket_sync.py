from __future__ import annotations

import csv
import gzip
import json
import mimetypes
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Iterable

from modules.infra.data_assets import build_data_assets_client, load_data_assets_settings
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_ROOT = _REPO_ROOT / "data"
_CARGA_PATTERN = re.compile(r"^data/raw/cabotage_data/(?P<year>\d{4})Carga\.txt$")
_CARGA_COLUMNS = (
    "IDAtracacao",
    "Tipo Navegação",
    "TEU",
    "Natureza da Carga",
    "Carga Geral Acondicionamento",
    "VLPesoCargaBruta",
    "Sentido",
    "Origem",
    "Destino",
)


@dataclass(frozen=True)
class UploadPlanItem:
    source_path: Path
    storage_object_path: str
    content_type: str
    transformed: bool
    compressed: bool
    payload_size_bytes: int
    payload: bytes
    manifest_object_path: str | None = None
    manifest_payload: bytes | None = None


def _parse_decimal(raw: str | None) -> float:
    text = (raw or "").strip()
    if not text:
        return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


def _is_containerized_cabotage(row: dict[str, str]) -> bool:
    if (row.get("Tipo Navegação", "") or "").strip().lower() != "cabotagem":
        return False

    if _parse_decimal(row.get("TEU")) > 0:
        return True

    natureza = (row.get("Natureza da Carga", "") or "").lower()
    acondicionamento = (row.get("Carga Geral Acondicionamento", "") or "").lower()
    return "conteiner" in natureza or "conteiner" in acondicionamento


def _relative_object_path(path: Path) -> str:
    return path.resolve().relative_to(_REPO_ROOT).as_posix()


def _guess_content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    return "application/octet-stream"


def build_filtered_carga_payload(path: Path) -> tuple[bytes, dict[str, Any]]:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(_CARGA_COLUMNS), delimiter=";")
    writer.writeheader()

    processed_rows = 0
    kept_rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            processed_rows += 1
            if not _is_containerized_cabotage(row):
                continue

            writer.writerow({column: row.get(column, "") for column in _CARGA_COLUMNS})
            kept_rows += 1

    payload = output.getvalue().encode("utf-8-sig")
    stats = {
        "processed_rows": processed_rows,
        "kept_rows": kept_rows,
        "kept_columns": list(_CARGA_COLUMNS),
        "transformation": "filter_containerized_cabotage_and_keep_required_columns",
    }
    return payload, stats


def _manifest_payload(
    *,
    source_path: Path,
    transformed: bool,
    compressed: bool,
    original_object_path: str,
    storage_object_path: str,
    payload_size_bytes: int,
    extra: dict[str, Any] | None = None,
) -> bytes:
    payload = {
        "source_path": _relative_object_path(source_path),
        "original_object_path": original_object_path,
        "storage_object_path": storage_object_path,
        "transformed": transformed,
        "compressed": compressed,
        "payload_size_bytes": payload_size_bytes,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def build_upload_plan(
    *,
    data_root: Path = _DEFAULT_DATA_ROOT,
    max_file_size_bytes: int = 50 * 1024 * 1024,
) -> list[UploadPlanItem]:
    plan: list[UploadPlanItem] = []

    for source_path in sorted(path for path in data_root.rglob("*") if path.is_file()):
        object_path = _relative_object_path(source_path)
        transformed = False
        compressed = False
        manifest_object_path: str | None = None
        manifest_payload: bytes | None = None

        payload: bytes
        extra_manifest: dict[str, Any] | None = None

        if _CARGA_PATTERN.match(object_path):
            payload, extra_manifest = build_filtered_carga_payload(source_path)
            transformed = True
        else:
            payload = source_path.read_bytes()

        storage_object_path = object_path
        if len(payload) > max_file_size_bytes:
            payload = gzip.compress(payload)
            compressed = True
            storage_object_path = f"{object_path}.gz"
            manifest_object_path = f"{object_path}.manifest.json"
            manifest_payload = _manifest_payload(
                source_path=source_path,
                transformed=transformed,
                compressed=compressed,
                original_object_path=object_path,
                storage_object_path=storage_object_path,
                payload_size_bytes=len(payload),
                extra=extra_manifest,
            )
        elif transformed:
            manifest_object_path = f"{object_path}.manifest.json"
            manifest_payload = _manifest_payload(
                source_path=source_path,
                transformed=transformed,
                compressed=compressed,
                original_object_path=object_path,
                storage_object_path=storage_object_path,
                payload_size_bytes=len(payload),
                extra=extra_manifest,
            )

        content_type = "application/gzip" if compressed else _guess_content_type(source_path)
        plan.append(
            UploadPlanItem(
                source_path=source_path,
                storage_object_path=storage_object_path,
                content_type=content_type,
                transformed=transformed,
                compressed=compressed,
                payload_size_bytes=len(payload),
                payload=payload,
                manifest_object_path=manifest_object_path,
                manifest_payload=manifest_payload,
            )
        )

    return plan


def execute_upload_plan(
    *,
    plan: Iterable[UploadPlanItem],
    bucket: str,
    dry_run: bool = False,
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    plan_list = list(plan)
    client = None if dry_run else build_data_assets_client(load_data_assets_settings())
    uploaded_files = 0
    uploaded_manifests = 0
    transformed_files = 0
    compressed_files = 0
    total_payload_bytes = 0

    for item in plan_list:
        total_payload_bytes += len(item.payload)
        if item.transformed:
            transformed_files += 1
        if item.compressed:
            compressed_files += 1

        _log.info(
            "data bucket sync: %s -> %s (%d bytes)%s%s",
            item.source_path,
            item.storage_object_path,
            item.payload_size_bytes,
            " transformed" if item.transformed else "",
            " compressed" if item.compressed else "",
        )

        if dry_run:
            continue

        assert client is not None
        client.upload_bytes(
            bucket=bucket,
            object_path=item.storage_object_path,
            payload=item.payload,
            content_type=item.content_type,
            upsert=True,
            timeout_s=timeout_s,
        )
        uploaded_files += 1

        if item.manifest_object_path and item.manifest_payload is not None:
            client.upload_bytes(
                bucket=bucket,
                object_path=item.manifest_object_path,
                payload=item.manifest_payload,
                content_type="application/json",
                upsert=True,
                timeout_s=timeout_s,
            )
            uploaded_manifests += 1

    return {
        "files_planned": len(plan_list),
        "uploaded_files": uploaded_files,
        "uploaded_manifests": uploaded_manifests,
        "transformed_files": transformed_files,
        "compressed_files": compressed_files,
        "total_payload_bytes": total_payload_bytes,
    }
