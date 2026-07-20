#!/usr/bin/env python3
"""Curate Geógrafos distance references for missing maritime matrix pairs.

This is an explicit maintenance command.  It never runs from Streamlit or
from the calculation pipeline: it records published port-pair distances in
``data/sea_matrix.json`` so runtime calculations remain deterministic and do
not depend on live web requests.

Only pairs without a positive primary ``matrix`` distance are considered.
Existing external references are preserved.  If Geógrafos has no page for the
registered port labels or aliases, no value is fabricated and Haversine remains
the clearly identified last-resort fallback at runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import requests


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.cabotage.geografos_distance_references import (
    GEOGRAFOS_CATALOG_URL,
    fetch_geografos_distance_reference,
)


DEFAULT_SEA_MATRIX_PATH = Path("data/sea_matrix.json")


class _RateLimitedSession:
    """Thin wrapper that spaces source-site requests in a refresh run."""

    def __init__(self, session: requests.Session, min_interval_s: float) -> None:
        self._session = session
        self._min_interval_s = max(0.0, float(min_interval_s))
        self._last_request_at = 0.0

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        wait_s = self._min_interval_s - (time.monotonic() - self._last_request_at)
        if wait_s > 0.0:
            time.sleep(wait_s)
        response = self._session.get(url, **kwargs)
        self._last_request_at = time.monotonic()
        return response


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0.0 else None


def _matrix_has_pair(matrix: dict[str, Any], origin: str, destination: str) -> bool:
    for source, target in ((origin, destination), (destination, origin)):
        row = matrix.get(source)
        if isinstance(row, dict) and _positive_float(row.get(target)) is not None:
            return True
    return False


def _external_reference_exists(
    references: dict[str, Any],
    origin: str,
    destination: str,
) -> bool:
    for source, target in ((origin, destination), (destination, origin)):
        row = references.get(source)
        if not isinstance(row, dict):
            continue
        reference = row.get(target)
        value = reference.get("distance_km") if isinstance(reference, dict) else reference
        if _positive_float(value) is not None:
            return True
    return False


def _slug_candidates(port: dict[str, Any]) -> list[str]:
    candidates = port.get("slug_candidates")
    if isinstance(candidates, list):
        values = [str(value) for value in candidates if str(value).strip()]
    else:
        values = []
    if not values and str(port.get("slug") or "").strip():
        values.append(str(port["slug"]))
    return values


def _missing_matrix_pairs(payload: dict[str, Any]) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    ports = payload.get("ports")
    matrix = payload.get("matrix")
    if not isinstance(ports, list) or not isinstance(matrix, dict):
        raise ValueError("Sea matrix payload requires 'ports' and 'matrix' objects.")
    for index, origin in enumerate(ports):
        if not isinstance(origin, dict) or not str(origin.get("name") or "").strip():
            continue
        for destination in ports[index + 1 :]:
            if not isinstance(destination, dict) or not str(destination.get("name") or "").strip():
                continue
            if not _matrix_has_pair(matrix, str(origin["name"]), str(destination["name"])):
                yield origin, destination


def refresh_geografos_distance_fallbacks(
    payload: dict[str, Any],
    *,
    timeout_s: float,
    min_interval_s: float,
    retrieved_at: str,
) -> dict[str, Any]:
    """Add source-verified fallbacks only for primary-matrix gaps."""

    references = payload.setdefault("external_distance_fallbacks", {})
    if not isinstance(references, dict):
        raise ValueError("'external_distance_fallbacks' must be an object when present.")

    session = _RateLimitedSession(requests.Session(), min_interval_s)
    added: list[dict[str, Any]] = []
    retained: list[tuple[str, str]] = []
    unavailable: list[tuple[str, str]] = []

    for origin, destination in _missing_matrix_pairs(payload):
        origin_name = str(origin["name"])
        destination_name = str(destination["name"])
        if _external_reference_exists(references, origin_name, destination_name):
            retained.append((origin_name, destination_name))
            continue

        origin_slugs = _slug_candidates(origin)
        destination_slugs = _slug_candidates(destination)
        if not origin_slugs or not destination_slugs:
            unavailable.append((origin_name, destination_name))
            continue

        reference = fetch_geografos_distance_reference(
            origin_slugs,
            destination_slugs,
            session=session,
            timeout_s=timeout_s,
            retrieved_at=retrieved_at,
        )
        if reference is None:
            unavailable.append((origin_name, destination_name))
            continue

        reference["source_catalog_url"] = GEOGRAFOS_CATALOG_URL
        references.setdefault(origin_name, {})[destination_name] = reference
        added.append(
            {
                "origin": origin_name,
                "destination": destination_name,
                "distance_km": reference["distance_km"],
                "source_url": reference["source_url"],
            }
        )

    return {
        "added": added,
        "retained": retained,
        "unavailable": unavailable,
        "catalog_url": GEOGRAFOS_CATALOG_URL,
        "retrieved_at": retrieved_at,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sea-matrix-json",
        type=Path,
        default=DEFAULT_SEA_MATRIX_PATH,
        help="Tracked enriched sea matrix to update (default: data/sea_matrix.json).",
    )
    parser.add_argument("--timeout-s", type=float, default=10.0)
    parser.add_argument(
        "--min-interval-s",
        type=float,
        default=0.12,
        help="Minimum time between source-site requests.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    path = args.sea_matrix_json
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    summary = refresh_geografos_distance_fallbacks(
        payload,
        timeout_s=float(args.timeout_s),
        min_interval_s=float(args.min_interval_s),
        retrieved_at=date.today().isoformat(),
    )

    if not args.dry_run:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "sea_matrix_json": str(path),
                "dry_run": bool(args.dry_run),
                "added_count": len(summary["added"]),
                "retained_count": len(summary["retained"]),
                "unavailable_count": len(summary["unavailable"]),
                "added": summary["added"],
                "unavailable": summary["unavailable"],
                "catalog_url": summary["catalog_url"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
