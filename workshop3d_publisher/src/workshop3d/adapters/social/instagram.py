"""Instagram promo adapter (square/vertical image + hashtags, link-in-bio).

Secrets from env ONLY: IG_USER_ID, IG_ACCESS_TOKEN.
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social
from ...models import ProductRecord, SocialResult


@register_social
class InstagramAdapter(SocialAdapter):
    key = "instagram"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        texts = record.metadata.get("SOCIAL_MEDIA_TEXTS", {}).get("instagram", {})
        link_note = " (link in bio)" if self.settings.get("link_in_bio", True) else f" {product_url}"
        body = f"{texts.get('text', '')}{link_note}\n{texts.get('hashtags', '')}"

        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set IG_USER_ID and IG_ACCESS_TOKEN to enable posting.")
        try:
            raise NotImplementedError("Instagram Graph API publish not wired yet. See README.")
        except Exception as exc:
            return SocialResult(platform=self.key, status="FAILED", message=str(exc))
