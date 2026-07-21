"""Small text helpers: ASCII slugs and safe file names."""
from __future__ import annotations

import re
import unicodedata

_POLISH_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o",
    "ś": "s", "ź": "z", "ż": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O",
    "Ś": "S", "Ź": "Z", "Ż": "Z",
})


def to_ascii(text: str) -> str:
    text = text.translate(_POLISH_MAP)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def slugify(text: str) -> str:
    """ASCII, lowercase, hyphen-separated slug."""
    ascii_text = to_ascii(text).lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-") or "product"


def file_token(text: str) -> str:
    """ASCII token for file names using underscores (spec section 7)."""
    ascii_text = to_ascii(text)
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "_", ascii_text)
    return ascii_text.strip("_") or "product"


def title_case(text: str) -> str:
    """Human title with normal spaces (keeps existing capitalisation words)."""
    cleaned = re.sub(r"[_\-]+", " ", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned
