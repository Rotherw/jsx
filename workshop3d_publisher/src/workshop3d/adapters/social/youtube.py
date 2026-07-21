"""YouTube promo adapter.

Community post with the product image when the channel supports it, or a
prepared Shorts description if video material exists. Never generates or
publishes an empty video just to host the product.
Secrets from env ONLY: YOUTUBE_ACCESS_TOKEN.
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social
from ...models import ProductRecord, SocialResult


@register_social
class YouTubeAdapter(SocialAdapter):
    key = "youtube"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("YOUTUBE_ACCESS_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        texts = record.metadata.get("SOCIAL_MEDIA_TEXTS", {}).get("youtube", {})
        body = f"{texts.get('text', '')}\n{product_url}\n{texts.get('hashtags', '')}"

        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN community post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set YOUTUBE_ACCESS_TOKEN to enable posting.")
        try:
            raise NotImplementedError("YouTube Data API publish not wired yet. See README.")
        except Exception as exc:
            return SocialResult(platform=self.key, status="FAILED", message=str(exc))
