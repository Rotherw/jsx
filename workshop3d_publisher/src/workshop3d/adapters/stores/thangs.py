"""Thangs store adapter.

Secrets from environment ONLY: THANGS_API_TOKEN
Behaviour mirrors the Cults3D adapter (DRY_RUN / NOT_CONNECTED / live).
"""
from __future__ import annotations

import os

from ..base import StoreAdapter, register_store
from ...models import ProductRecord, StoreResult
from ...text_utils import slugify


@register_store
class ThangsAdapter(StoreAdapter):
    key = "thangs"
    supports_formats = ("stl", "3mf", "glb")

    def credentials_present(self) -> bool:
        return bool(os.environ.get("THANGS_API_TOKEN"))

    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        meta = record.metadata
        title = meta.get("TITLE", record.folder_name)

        if self.config.dry_run:
            slug = meta.get("SLUG", slugify(title))
            return StoreResult(
                platform=self.key,
                status="DRY_RUN",
                url=f"https://thangs.com/designer/WorkShop3D/3d-model/{slug}",
                message="DRY_RUN: listing prepared, not published.",
            )

        if not self.credentials_present():
            return StoreResult(
                platform=self.key,
                status="NOT_CONNECTED",
                message="Set THANGS_API_TOKEN to enable publishing.",
            )

        try:
            raise NotImplementedError(
                "Thangs live upload not wired yet. See README 'Connecting Thangs'."
            )
        except Exception as exc:
            return StoreResult(platform=self.key, status="FAILED", message=f"Thangs error: {exc}")
