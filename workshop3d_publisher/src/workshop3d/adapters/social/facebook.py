"""Facebook promo adapter.

Posts a short PL description + product image + link + hashtags via the Graph
API. Secrets from env ONLY: FB_PAGE_ID, FB_PAGE_TOKEN.
Promotion runs only AFTER at least one store listing succeeded and a real
product URL exists (enforced by the pipeline).
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social
from ...models import ProductRecord, SocialResult


@register_social
class FacebookAdapter(SocialAdapter):
    key = "facebook"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        texts = record.metadata.get("SOCIAL_MEDIA_TEXTS", {}).get("facebook", {})
        body = f"{texts.get('text', '')}\n{product_url}\n{texts.get('hashtags', '')}"

        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set FB_PAGE_ID and FB_PAGE_TOKEN to enable posting.")
        try:
            raise NotImplementedError("Facebook Graph API publish not wired yet. See README.")
        except Exception as exc:
            return SocialResult(platform=self.key, status="FAILED", message=str(exc))
