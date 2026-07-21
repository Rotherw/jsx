"""Creality Cloud EU store adapter (browser-automation strategy).

Creality Cloud has no public publishing API, so this adapter is designed for
browser automation reusing an EXISTING logged-in session. It must never:
  * bypass CAPTCHA,
  * bypass 2FA,
  * store passwords in code.
On any login/CAPTCHA block it stops THIS adapter only and asks the user to act.
"""
from __future__ import annotations

from ..base import StoreAdapter, register_store
from ...models import ProductRecord, StoreResult


@register_store
class CrealityCloudEUAdapter(StoreAdapter):
    key = "creality_cloud_eu"
    supports_formats = ("stl", "3mf")

    def credentials_present(self) -> bool:
        # "Credentials" here = an available logged-in browser session profile.
        import os
        return bool(os.environ.get("CREALITY_EU_BROWSER_PROFILE"))

    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        if self.config.dry_run:
            return StoreResult(
                platform=self.key,
                status="DRY_RUN",
                url="https://www.crealitycloud.com/model-detail/DRYRUN",
                message="DRY_RUN: listing prepared, browser automation not run.",
            )
        if not self.credentials_present():
            return StoreResult(
                platform=self.key,
                status="NOT_CONNECTED",
                message="No logged-in browser session (set CREALITY_EU_BROWSER_PROFILE).",
            )
        return StoreResult(
            platform=self.key,
            status="NEEDS_ATTENTION",
            message="Browser automation requires manual confirmation. See README.",
        )
