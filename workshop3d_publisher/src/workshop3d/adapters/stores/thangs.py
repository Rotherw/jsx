"""Thangs store adapter.

Thangs has no public *upload* API. Its official automation path is the
**Thangs Sync** desktop client, which watches a folder and uploads each
subfolder as a model, reading metadata from a CSV
(columns: ModelName, Description, Tags, Category, SecondaryCategory;
tags separated by ':').

This adapter can run through the paired Chrome extension (recommended) or in
"sync" mode: it stages the product's files into
a subfolder of your Thangs Sync watched folder and writes/updates the metadata
CSV row. The official Thangs Sync client (logged in as you) performs the actual
upload. The adapter never logs in for you and never fakes a completed upload --
it reports STAGED and tells you to run/confirm Thangs Sync.

An "api" mode is kept as a guarded placeholder in case Thangs publishes a real
upload API later (token: THANGS_API_TOKEN).
"""
from __future__ import annotations

import csv
import os
import shutil
from pathlib import Path

from ..base import StoreAdapter, register_store
from ...models import ProductRecord, StoreResult
from ...text_utils import slugify

_CSV_NAME = "thangs_bulk_upload.csv"
_CSV_COLUMNS = ["ModelName", "Description", "Tags", "Category", "SecondaryCategory"]
_ILLEGAL = '\\/:*?"<>|'


def _safe_folder(name: str) -> str:
    cleaned = "".join("_" if ch in _ILLEGAL else ch for ch in name).strip()
    return cleaned or "model"


@register_store
class ThangsAdapter(StoreAdapter):
    key = "thangs"
    supports_formats = ("stl", "3mf", "glb")

    def _mode(self) -> str:
        return str(self.settings.get("mode", "sync"))

    def credentials_present(self) -> bool:
        if self._mode() == "browser":
            from ...browser_bridge import BrowserBridge
            return BrowserBridge.shared(self.config).status()["connected"]
        if self._mode() == "api":
            return bool(os.environ.get("THANGS_API_TOKEN"))
        # sync mode: "connected" means a Thangs Sync watched folder is set.
        return bool(self.settings.get("sync_folder"))

    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        meta = record.metadata
        title = meta.get("TITLE", record.folder_name)

        if self.config.dry_run:
            slug = meta.get("SLUG", slugify(title))
            return StoreResult(
                platform=self.key, status="DRY_RUN",
                url=f"https://thangs.com/designer/WorkShop3D/3d-model/{slug}",
                message="DRY_RUN: files + metadata staged for Thangs Sync (not uploaded).",
            )

        if self._mode() == "browser":
            from ...browser_bridge import queue_browser_publish
            return queue_browser_publish(self.config, self.settings, self.key, record, workspace)

        if self._mode() == "api":
            if not os.environ.get("THANGS_API_TOKEN"):
                return StoreResult(platform=self.key, status="NOT_CONNECTED",
                                   message="Set THANGS_API_TOKEN to enable API mode.")
            return StoreResult(
                platform=self.key, status="FAILED",
                message="Thangs has no public upload API. Use stores.thangs.mode: 'sync'.",
            )

        return self._stage_for_sync(record, workspace, title)

    # -- sync mode ----------------------------------------------------------
    def _stage_for_sync(self, record: ProductRecord, workspace: str, title: str) -> StoreResult:
        folder = self.settings.get("sync_folder")
        if not folder:
            return StoreResult(
                platform=self.key, status="NOT_CONNECTED",
                message="Set stores.thangs.sync_folder to your Thangs Sync watched folder.",
            )
        sync_root = Path(folder)
        try:
            sync_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return StoreResult(platform=self.key, status="FAILED",
                               message=f"Cannot use Thangs Sync folder: {exc}")

        model_dir = sync_root / _safe_folder(title)
        model_dir.mkdir(parents=True, exist_ok=True)

        files_dir = Path(workspace) / "files"
        copied = 0
        if files_dir.exists():
            for p in sorted(files_dir.glob("*")):
                if p.suffix.lower() in (".stl", ".3mf", ".glb", ".png"):
                    shutil.copy2(p, model_dir / p.name)
                    copied += 1
        if copied == 0:
            return StoreResult(platform=self.key, status="FAILED",
                               message="No model/image files found to stage for Thangs.")

        self._upsert_csv_row(sync_root, model_dir.name, record.metadata)

        brand = self.config.get("brand.name", "WorkShop3D")
        return StoreResult(
            platform=self.key, status="STAGED",
            url=f"https://thangs.com/designer/{brand}",
            message=(f"Staged {copied} files + metadata in '{model_dir.name}'. "
                     "Open Thangs Sync and press Start Upload to publish."),
        )

    def _upsert_csv_row(self, sync_root: Path, model_name: str, meta: dict) -> None:
        csv_path = sync_root / _CSV_NAME
        rows: list[dict] = []
        if csv_path.exists():
            try:
                with open(csv_path, "r", encoding="utf-8", newline="") as fh:
                    rows = [r for r in csv.DictReader(fh) if r.get("ModelName")]
            except Exception:
                rows = []

        tags = ":".join(meta.get("TAGS", [])[: int(self.settings.get("max_tags", 20))])
        cat_map = self.settings.get("category_map", {}) or {}
        category = cat_map.get(meta.get("CATEGORY"), meta.get("CATEGORY", ""))
        coll = (meta.get("_collection") or {})
        secondary = self.settings.get("secondary_category", "")

        row = {
            "ModelName": model_name,
            "Description": meta.get("DESCRIPTION_EN", ""),
            "Tags": tags,
            "Category": category or "",
            "SecondaryCategory": secondary,
        }
        # Idempotent upsert by ModelName.
        rows = [r for r in rows if r.get("ModelName") != model_name]
        rows.append(row)

        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in _CSV_COLUMNS})
