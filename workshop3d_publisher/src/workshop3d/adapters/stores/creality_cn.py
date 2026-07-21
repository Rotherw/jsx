"""Creality Cloud CN store adapter (browser-automation strategy).

Same rules and safeguards as the EU adapter.
"""
from __future__ import annotations

import os

from ..base import StoreAdapter, register_store
from ...models import ProductRecord, StoreResult


@register_store
class CrealityCloudCNAdapter(StoreAdapter):
    key = "creality_cloud_cn"
    supports_formats = ("stl", "3mf")

    def credentials_present(self) -> bool:
        return bool(os.environ.get("CREALITY_CN_BROWSER_PROFILE"))

    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        if self.config.dry_run:
            return StoreResult(
                platform=self.key,
                status="DRY_RUN",
                url="https://www.crealitycloud.cn/model-detail/DRYRUN",
                message="DRY_RUN: listing prepared, browser automation not run.",
            )
        if not self.credentials_present():
            return StoreResult(
                platform=self.key,
                status="NOT_CONNECTED",
                message="No logged-in browser session (set CREALITY_CN_BROWSER_PROFILE).",
            )
        return StoreResult(
            platform=self.key,
            status="NEEDS_ATTENTION",
            message="Browser automation requires manual confirmation. See README.",
        )
