"""Pinterest promo adapter.

Creating a Pin needs a Pinterest developer app (OAuth) plus a public image URL
and a target board id. This adapter prepares the Pin and stops honestly at
NOT_CONNECTED / a marked connection point rather than faking a Pin.
Secrets from env ONLY (when wired):
    PINTEREST_ACCESS_TOKEN, PINTEREST_BOARD_ID
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult


@register_social
class PinterestAdapter(SocialAdapter):
    key = "pinterest"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("PINTEREST_ACCESS_TOKEN") and os.environ.get("PINTEREST_BOARD_ID"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        body = compose_post(record, "pinterest", product_url)
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN pin prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID.")
        try:
            raise NotImplementedError(
                "Pinterest Pin creation (POST /v5/pins) not wired yet; needs a public "
                "image URL + board id. See README."
            )
        except Exception as exc:
            return SocialResult(platform=self.key, status="FAILED", message=str(exc))
