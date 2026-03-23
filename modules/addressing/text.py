from __future__ import annotations

import re
import unicodedata
from typing import Any


def strip_accents(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def clean_place_text(label: Any) -> str:
    text = str(label or "").strip()
    if not text:
        return ""

    text = re.sub(r"\s*,\s*(?:brazil|brasil)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*[/-]\s*([A-Za-z]{2})\s*$", r", \1", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*,\s*,+", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,")


def ascii_place_text(label: Any) -> str:
    return clean_place_text(strip_accents(label))


def ascii_place_key(label: Any) -> str:
    return ascii_place_text(label).casefold()
