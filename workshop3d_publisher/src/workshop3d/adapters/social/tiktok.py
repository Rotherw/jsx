"""TikTok promo adapter.

Photo mode when the platform supports it. Never fabricates a video when only a
PNG was delivered. Secrets from env ONLY: TIKTOK_ACCESS_TOKEN.
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social
from ...models import ProductRecord, SocialResult


@register_social
class TikTokAdapter(SocialAdapter):
    key = "tiktok"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("TIKTOK_ACCESS_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        texts = record.metadata.get("SOCIAL_MEDIA_TEXTS", {}).get("tiktok", {})
        body = f"{texts.get('text', '')} (link in profile)\n{texts.get('hashtags', '')}"

        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN photo-mode post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set TIKTOK_ACCESS_TOKEN to enable posting.")
        try:
            raise NotImplementedError("TikTok content API publish not wired yet. See README.")
        except Exception as exc:
            return SocialResult(platform=self.key, status="FAILED", message=str(exc))
