"""Persistent, crash-safe store of product records.

State is written to a JSON file so a program/computer restart never loses
progress. Writes are atomic (temp file + os.replace). A threading lock guards
concurrent access from the watcher thread and the dashboard thread.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Iterator, Optional

from .models import ProductRecord


class StateStore:
    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records: dict[str, ProductRecord] = {}
        self._load()

    # --- persistence -------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Corrupt state file: keep a backup, start clean rather than crash.
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            return
        for rec in data.get("products", []):
            r = ProductRecord.from_dict(rec)
            self._records[r.product_id] = r

    def _flush_locked(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        payload = {"products": [r.to_dict() for r in self._records.values()]}
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    # --- public API --------------------------------------------------------
    def get(self, product_id: str) -> Optional[ProductRecord]:
        with self._lock:
            return self._records.get(product_id)

    def find_by_folder(self, folder_name: str) -> Optional[ProductRecord]:
        with self._lock:
            for r in self._records.values():
                if r.folder_name == folder_name:
                    return r
            return None

    def upsert(self, record: ProductRecord) -> None:
        with self._lock:
            record.touch()
            self._records[record.product_id] = record
            self._flush_locked()

    def remove(self, product_id: str) -> None:
        with self._lock:
            if product_id in self._records:
                del self._records[product_id]
                self._flush_locked()

    def rekey(self, old_id: str, record: ProductRecord) -> None:
        """Move a record to a new product_id key, dropping the old entry."""
        with self._lock:
            self._records.pop(old_id, None)
            record.touch()
            self._records[record.product_id] = record
            self._flush_locked()

    def all(self) -> list[ProductRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda r: r.detected_at)

    def __iter__(self) -> Iterator[ProductRecord]:
        return iter(self.all())

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
