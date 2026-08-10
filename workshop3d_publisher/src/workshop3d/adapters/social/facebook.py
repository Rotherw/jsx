"""Facebook Page promo adapter (fully wired to the Graph API).

Posts a link + message to a Facebook Page. You still need a Meta developer app
and a **Page access token** (a normal FB account is not enough -- that's Meta's
security, no code can bypass it). Secrets from env ONLY:
    FB_PAGE_ID, FB_PAGE_TOKEN   (token scope: pages_manage_posts)
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult
from ._nethttp import post_form, SocialHTTPError

_GRAPH = "https://graph.facebook.com/v21.0"


@register_social
class FacebookAdapter(SocialAdapter):
    key = "facebook"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        body = compose_post(record, "facebook", product_url)
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set FB_PAGE_ID and FB_PAGE_TOKEN (Page access token).")
        page_id = os.environ["FB_PAGE_ID"]
        token = os.environ["FB_PAGE_TOKEN"]
        fields = {"message": body, "access_token": token}
        if product_url:
            fields["link"] = product_url
        try:
            res = post_form(f"{_GRAPH}/{page_id}/feed", fields)
        except SocialHTTPError as exc:
            return SocialResult(platform=self.key, status="FAILED", message=f"Facebook: {exc}")
        post_id = res.get("id", "")
        url = f"https://www.facebook.com/{post_id}" if post_id else None
        return SocialResult(platform=self.key, status="POSTED", post_url=url,
                            message="Posted to Facebook Page.")
