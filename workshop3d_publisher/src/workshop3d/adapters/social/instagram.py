"""Instagram promo adapter (fully wired to the Graph API).

Instagram publishing is a two-step Graph API flow (create media container ->
publish) and needs a **public image URL**, which we host via the same asset
host as Cults3D (Google Drive by default). Requires an Instagram Business/
Creator account linked to a Page + a Meta app. Secrets from env ONLY:
    IG_USER_ID, IG_ACCESS_TOKEN
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult
from ._nethttp import post_form, SocialHTTPError
from ._media import hosted_cover_url

_GRAPH = "https://graph.facebook.com/v21.0"


@register_social
class InstagramAdapter(SocialAdapter):
    key = "instagram"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        link_mode = "bio" if self.settings.get("link_in_bio", True) else "url"
        caption = compose_post(record, "instagram", product_url, link_mode=link_mode)
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{caption}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set IG_USER_ID and IG_ACCESS_TOKEN.")

        image_url = hosted_cover_url(record, self.config, workspace)
        if not image_url:
            return SocialResult(platform=self.key, status="NEEDS_ATTENTION",
                                message="Instagram needs a public image URL. Configure the Google Drive asset host.")

        ig_user = os.environ["IG_USER_ID"]
        token = os.environ["IG_ACCESS_TOKEN"]
        try:
            container = post_form(f"{_GRAPH}/{ig_user}/media",
                                  {"image_url": image_url, "caption": caption, "access_token": token})
            creation_id = container.get("id")
            if not creation_id:
                return SocialResult(platform=self.key, status="FAILED",
                                    message="Instagram: no media container id returned.")
            published = post_form(f"{_GRAPH}/{ig_user}/media_publish",
                                  {"creation_id": creation_id, "access_token": token})
        except SocialHTTPError as exc:
            return SocialResult(platform=self.key, status="FAILED", message=f"Instagram: {exc}")
        media_id = published.get("id", "")
        return SocialResult(platform=self.key, status="POSTED",
                            post_url=f"https://www.instagram.com/p/{media_id}" if media_id else None,
                            message="Posted to Instagram.")
