"""Published maritime-distance references from Geógrafos.

This module is deliberately limited to collecting and validating an exact
port-pair distance published by Geógrafos.  It does not alter the sea matrix
and must not be called from the user-facing calculation path.  A maintenance
workflow can use its output to curate ``external_distance_fallbacks`` in the
tracked matrix when no observed ANTAQ corridor is available.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any, Protocol

import requests
from bs4 import BeautifulSoup

from modules.infra.log_manager import get_logger

__all__ = [
    "GEOGRAFOS_CATALOG_URL",
    "GEOGRAFOS_SOURCE_LABEL",
    "build_geografos_direct_port_pair_url",
    "candidate_geografos_direct_port_pair_urls",
    "fetch_geografos_distance_reference",
    "fetch_geografos_direct_distance_reference",
    "parse_geografos_direct_distance_html",
    "port_slug",
]


_log = get_logger(__name__)

GEOGRAFOS_BASE_URL = "https://www.geografos.com.br"
GEOGRAFOS_CATALOG_URL = f"{GEOGRAFOS_BASE_URL}/distancias-maritimas-entre-portos/"
GEOGRAFOS_SOURCE_LABEL = "Geógrafos — Distâncias Marítimas Entre Portos"
_DIRECT_PORT_PAIR_PATH = (
    "viagem-maritima-entre-portos-brasil/"
    "distancia-entre-porto-{origin_slug}-e-porto-{destination_slug}.php"
)
_USER_AGENT = "cabotagelens/1.0 (academic maritime-distance reference collector)"

_ORIGIN_RE = re.compile(
    r"Porto\s+de\s+Origem\s*:\s*(?P<origin>.+?)"
    r"(?=\s+Porto\s+(?:do|de)\s+Destino\s*:)",
    flags=re.IGNORECASE | re.DOTALL,
)
_DESTINATION_RE = re.compile(
    r"Porto\s+(?:do|de)\s+Destino\s*:\s*(?P<destination>.+?)"
    r"(?=\s+Dist[âa]ncia\s*:)",
    flags=re.IGNORECASE | re.DOTALL,
)
_DISTANCE_RE = re.compile(
    r"Dist[âa]ncia\s*:\s*"
    r"(?P<distance_km>[0-9][0-9.,\s]*)\s*Km\s+ou\s*"
    r"(?P<distance_nm>[0-9][0-9.,\s]*)\s*Milhas?\s+N[áa]uticas",
    flags=re.IGNORECASE | re.DOTALL,
)
_STATE_SUFFIX_RE = re.compile(r"\s*[-–]\s*[A-Za-z]{2}\s*$")
_INVALID_SLUG_RE = re.compile(r"[^a-z0-9-]")


class _ResponseLike(Protocol):
    """Small response surface used to keep the HTTP boundary injectable."""

    text: str
    status_code: int
    url: str

    def raise_for_status(self) -> None: ...


class _SessionLike(Protocol):
    def get(self, url: str, **kwargs: Any) -> _ResponseLike: ...


def port_slug(value: str) -> str:
    """Return the URL slug used by Geógrafos for a supplied port name/slug.

    The site URLs use unaccented lower-case names separated by hyphens.  This
    helper also accepts a common display form such as ``"Porto de Santos"``
    or ``"Vila do Conde - PA"`` so the verification performed after fetching
    uses the same normalization as the candidate URL construction.
    """

    text = str(value or "").strip()
    text = _STATE_SUFFIX_RE.sub("", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.casefold()
    text = re.sub(r"\bporto\s+(?:de|do|da)\s+", "", text)
    text = re.sub(r"\bporto\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"^porto-+", "", text)
    text = re.sub(r"-{2,}", "-", text)
    if not text or _INVALID_SLUG_RE.search(text):
        raise ValueError(f"Invalid Geógrafos port slug: {value!r}")
    return text


def build_geografos_direct_port_pair_url(origin_slug: str, destination_slug: str) -> str:
    """Build the direct Geógrafos page URL for one ordered pair of ports."""

    origin = port_slug(origin_slug)
    destination = port_slug(destination_slug)
    return f"{GEOGRAFOS_BASE_URL}/{_DIRECT_PORT_PAIR_PATH.format(origin_slug=origin, destination_slug=destination)}"


def candidate_geografos_direct_port_pair_urls(
    origin_slug: str,
    destination_slug: str,
) -> tuple[str, ...]:
    """Return candidate Geógrafos direct-page URLs in both port directions.

    Some source pages are published in only one ordering.  Trying both URLs
    does not assume that the calculated maritime distance is directionally
    different; a verified source is stored as a symmetric external reference.
    """

    origin = port_slug(origin_slug)
    destination = port_slug(destination_slug)
    forward = build_geografos_direct_port_pair_url(origin, destination)
    if origin == destination:
        return (forward,)
    reverse = build_geografos_direct_port_pair_url(destination, origin)
    return (forward, reverse)


def parse_geografos_direct_distance_html(html: str) -> dict[str, Any]:
    """Parse and validate the port names plus km/nm values from one source page.

    ``ValueError`` means that the page does not have the expected direct
    Geógrafos port-pair structure.  The caller can then try the reverse URL or
    leave the pair without an external reference.
    """

    if not isinstance(html, str) or not html.strip():
        raise ValueError("Geógrafos page is empty or is not HTML text.")

    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    origin_match = _ORIGIN_RE.search(text)
    destination_match = _DESTINATION_RE.search(text)
    distance_match = _DISTANCE_RE.search(text)
    if not origin_match or not destination_match or not distance_match:
        raise ValueError(
            "Could not identify the origin, destination, and km/nm distance "
            "in the Geógrafos direct port-pair page."
        )

    origin_port = _clean_page_port_name(origin_match.group("origin"))
    destination_port = _clean_page_port_name(destination_match.group("destination"))
    distance_km = _parse_published_number(distance_match.group("distance_km"))
    distance_nm = _parse_published_number(distance_match.group("distance_nm"))
    if not origin_port or not destination_port or distance_km <= 0.0 or distance_nm <= 0.0:
        raise ValueError("Geógrafos direct port-pair page contains invalid port or distance data.")

    return {
        "page_origin_port": origin_port,
        "page_destination_port": destination_port,
        "distance_km": distance_km,
        "reported_distance_nm": distance_nm,
    }


def fetch_geografos_direct_distance_reference(
    origin_slug: str,
    destination_slug: str,
    *,
    session: _SessionLike | None = None,
    timeout_s: float = 20.0,
    retrieved_at: date | datetime | str | None = None,
) -> dict[str, Any] | None:
    """Fetch one verified Geógrafos distance entry for an exact port pair.

    The forward page is tried first and the reverse page second.  A page is
    accepted only when its own origin/destination labels match the URL pair;
    this avoids treating a generic, redirected, or unrelated page as a
    distance reference.  ``None`` is returned when neither direction provides
    a verified direct reference.

    This function is intended for an explicit refresh/curation workflow, not
    the runtime calculation pipeline.
    """

    origin = port_slug(origin_slug)
    destination = port_slug(destination_slug)
    sess = session or requests.Session()
    retrieved_date = _as_iso_date(retrieved_at)
    candidates = candidate_geografos_direct_port_pair_urls(origin, destination)

    for candidate_url in candidates:
        expected_origin, expected_destination = _candidate_pair_from_url(
            candidate_url,
            origin=origin,
            destination=destination,
        )
        try:
            response = sess.get(
                candidate_url,
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout_s,
            )
            status_code = int(getattr(response, "status_code", 200))
            if status_code != 200:
                _log.debug(
                    "Geógrafos does not provide %s (HTTP %s).",
                    candidate_url,
                    status_code,
                )
                continue
            response.raise_for_status()
        except requests.RequestException as exc:
            _log.debug("Failed to fetch Geógrafos page %s: %s", candidate_url, exc)
            continue
        except Exception as exc:  # Covers a lightweight injectable response/session.
            _log.debug("Failed to read Geógrafos page %s: %s", candidate_url, exc)
            continue

        try:
            parsed = parse_geografos_direct_distance_html(response.text)
        except ValueError as exc:
            _log.debug("Could not parse Geógrafos page %s: %s", candidate_url, exc)
            continue

        page_origin = port_slug(parsed["page_origin_port"])
        page_destination = port_slug(parsed["page_destination_port"])
        if (page_origin, page_destination) != (expected_origin, expected_destination):
            _log.warning(
                "Ignoring Geógrafos page with mismatched pair: requested %s -> %s, "
                "page reports %s -> %s (%s).",
                expected_origin,
                expected_destination,
                page_origin,
                page_destination,
                candidate_url,
            )
            continue

        resolved_url = str(getattr(response, "url", "") or candidate_url)
        return {
            "distance_km": parsed["distance_km"],
            "reported_distance_nm": parsed["reported_distance_nm"],
            "source": "geografos_reference",
            "source_label": GEOGRAFOS_SOURCE_LABEL,
            "source_type": "external_reference",
            "source_url": resolved_url,
            "retrieved_at": retrieved_date,
            "symmetric": True,
            "source_page_origin_port": parsed["page_origin_port"],
            "source_page_destination_port": parsed["page_destination_port"],
            "requested_origin_slug": origin,
            "requested_destination_slug": destination,
            "matched_page_origin_slug": page_origin,
            "matched_page_destination_slug": page_destination,
            "matched_candidate_direction": (
                "forward" if (expected_origin, expected_destination) == (origin, destination) else "reverse"
            ),
            "notes": (
                "Distância publicada para o par de portos no Geógrafos; "
                "não representa, por si só, uma viagem ANTAQ observada."
            ),
        }

    return None


def fetch_geografos_distance_reference(
    origin_slug_candidates: list[str] | tuple[str, ...],
    destination_slug_candidates: list[str] | tuple[str, ...],
    *,
    session: _SessionLike | None = None,
    timeout_s: float = 20.0,
    retrieved_at: date | datetime | str | None = None,
) -> dict[str, Any] | None:
    """Fetch a verified reference using registered aliases for both ports.

    The caller supplies the canonical Geógrafos slug followed by any aliases
    registered for each CabotageLens port.  Each combination is verified
    against the labels published on the source page.  The first valid result
    is sufficient because a fallback represents a static port-pair distance,
    not an observed ANTAQ service itinerary.
    """

    origin_candidates = _unique_normalized_slugs(origin_slug_candidates)
    destination_candidates = _unique_normalized_slugs(destination_slug_candidates)
    if not origin_candidates or not destination_candidates:
        raise ValueError("At least one Geógrafos slug is required for each port.")

    sess = session or requests.Session()
    for origin in origin_candidates:
        for destination in destination_candidates:
            reference = fetch_geografos_direct_distance_reference(
                origin,
                destination,
                session=sess,
                timeout_s=timeout_s,
                retrieved_at=retrieved_at,
            )
            if reference is None:
                continue
            reference["requested_origin_slug_candidates"] = origin_candidates
            reference["requested_destination_slug_candidates"] = destination_candidates
            return reference
    return None


def _candidate_pair_from_url(
    candidate_url: str,
    *,
    origin: str,
    destination: str,
) -> tuple[str, str]:
    """Resolve expected page direction without relying on URL string parsing."""

    forward = build_geografos_direct_port_pair_url(origin, destination)
    if candidate_url == forward:
        return origin, destination
    return destination, origin


def _clean_page_port_name(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _parse_published_number(value: str) -> float:
    """Parse a Brazilian-formatted whole or decimal number published on a page."""

    text = "".join(str(value or "").replace("\xa0", " ").split())
    if not text or not re.fullmatch(r"[0-9][0-9.,]*", text):
        raise ValueError(f"Invalid published distance number: {value!r}")

    if "." in text and "," in text:
        if text.rfind(",") > text.rfind("."):
            normalized = text.replace(".", "").replace(",", ".")
        else:
            normalized = text.replace(",", "")
    elif "." in text:
        normalized = text.replace(".", "") if _is_grouped_thousands(text, ".") else text
    elif "," in text:
        normalized = text.replace(",", "") if _is_grouped_thousands(text, ",") else text.replace(",", ".")
    else:
        normalized = text

    try:
        number = float(normalized)
    except ValueError as exc:  # pragma: no cover - guarded above, retained defensively
        raise ValueError(f"Invalid published distance number: {value!r}") from exc
    if number <= 0.0:
        raise ValueError(f"Published distance must be positive: {value!r}")
    return number


def _is_grouped_thousands(value: str, separator: str) -> bool:
    return bool(re.fullmatch(rf"[0-9]{{1,3}}(?:\{separator}[0-9]{{3}})+", value))


def _as_iso_date(value: date | datetime | str | None) -> str:
    if value is None:
        return date.today().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        raise ValueError("retrieved_at must be an ISO date when provided.")
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError("retrieved_at must be an ISO date when provided.") from exc


def _unique_normalized_slugs(values: list[str] | tuple[str, ...]) -> list[str]:
    unique: list[str] = []
    for value in values:
        normalized = port_slug(value)
        if normalized not in unique:
            unique.append(normalized)
    return unique
