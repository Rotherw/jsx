"""Persistent listing manager for central PL/EN marketplace metadata."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .text_utils import slugify

_PLATFORM_EXPORTS = (
    ("thangs", "Thangs", "EN", 20),
    ("cults3d", "Cults3D", "EN", 20),
    ("creality_cloud_int", "Creality Cloud INT", "EN", 20),
    ("creality_cloud_cn", "Creality Cloud CN", "EN", 20),
    ("myminifactory", "MyMiniFactory", "EN", 15),
    ("printables", "Printables", "EN", 15),
)


def _clean_text(value: str) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", _clean_text(value))


def parse_tags(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\n]+", str(value or ""))
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in raw_items:
        tag = re.sub(r"\s+", " ", str(item).strip())
        if not tag:
            continue
        token = tag.casefold()
        if token in seen:
            continue
        seen.add(token)
        cleaned.append(tag)
    return cleaned


def normalize_links(values: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for platform, url in (values or {}).items():
        link = str(url or "").strip()
        if link:
            cleaned[platform] = link
    return cleaned


@dataclass
class ListingRecord:
    listing_id: str
    slug: str
    title_pl: str = ""
    title_en: str = ""
    description_pl: str = ""
    description_en: str = ""
    tags: list[str] = field(default_factory=list)
    links: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ListingRecord":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        record = cls(**{k: v for k, v in data.items() if k in known})
        record.title_pl = _clean_title(record.title_pl)
        record.title_en = _clean_title(record.title_en)
        record.description_pl = _clean_text(record.description_pl)
        record.description_en = _clean_text(record.description_en)
        record.tags = parse_tags(record.tags)
        record.links = normalize_links(record.links)
        record.slug = slugify(record.slug or record.title_en or record.title_pl or record.listing_id)
        return record


class ListingStore:
    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records: dict[str, ListingRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            return
        for rec in data.get("listings", []):
            record = ListingRecord.from_dict(rec)
            self._records[record.listing_id] = record

    def _flush_locked(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        payload = {"listings": [r.to_dict() for r in self._records.values()]}
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, listing_id: str | None) -> ListingRecord | None:
        if not listing_id:
            return None
        with self._lock:
            return self._records.get(listing_id)

    def upsert(self, record: ListingRecord) -> None:
        with self._lock:
            record.touch()
            self._records[record.listing_id] = record
            self._flush_locked()

    def all(self) -> list[ListingRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda r: (r.updated_at, r.created_at))


def listing_warnings(record: ListingRecord) -> list[str]:
    warnings: list[str] = []
    if not record.title_pl:
        warnings.append("Brakuje polskiego tytułu.")
    if not record.title_en:
        warnings.append("Brakuje angielskiego tytułu.")
    if not record.description_pl:
        warnings.append("Brakuje polskiego opisu.")
    if not record.description_en:
        warnings.append("Brakuje angielskiego opisu.")
    if not record.tags:
        warnings.append("Brakuje tagów.")
    typo_targets = {
        "WorShop3D": "WorkShop3D",
        "Work Shop 3D": "WorkShop3D",
    }
    for bad, good in typo_targets.items():
        for field_name, value in (
            ("tytuł PL", record.title_pl),
            ("tytuł EN", record.title_en),
            ("opis PL", record.description_pl),
            ("opis EN", record.description_en),
        ):
            if bad.casefold() in value.casefold():
                warnings.append(f"{field_name}: popraw literówkę „{bad}” → „{good}”.")
    for platform, url in record.links.items():
        if url.startswith("@"):
            warnings.append(f"{platform}: link wygląda jak sam handle „@”, a nie pełny URL.")
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            warnings.append(f"{platform}: niepoprawny link „{url}”.")
    return warnings


def export_payload(record: ListingRecord) -> list[dict]:
    exports: list[dict] = []
    for key, label, language, tag_limit in _PLATFORM_EXPORTS:
        tags = record.tags[:tag_limit]
        export_warnings: list[str] = []
        if len(record.tags) > tag_limit:
            export_warnings.append(f"Ucięto tagi do limitu {tag_limit}.")
        exports.append({
            "key": key,
            "label": label,
            "language": language,
            "title": record.title_en or record.title_pl,
            "description": record.description_en or record.description_pl,
            "tags": tags,
            "tag_limit": tag_limit,
            "link": record.links.get(key, ""),
            "warnings": export_warnings,
        })
    return exports
