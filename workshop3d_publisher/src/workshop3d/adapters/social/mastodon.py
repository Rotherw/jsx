"""Mastodon promo adapter (fully wired).

Mastodon's API is simple token auth, so this really posts.
Secrets from env ONLY:
    MASTODON_INSTANCE_URL  (e.g. https://mastodon.social)
    MASTODON_ACCESS_TOKEN  (Preferences -> Development -> New application, scope write:statuses)
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult
from ._nethttp import post_form, SocialHTTPError


@register_social
class MastodonAdapter(SocialAdapter):
    key = "mastodon"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("MASTODON_INSTANCE_URL") and os.environ.get("MASTODON_ACCESS_TOKEN"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        body = compose_post(record, "mastodon", product_url)
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set MASTODON_INSTANCE_URL and MASTODON_ACCESS_TOKEN.")
        base = os.environ["MASTODON_INSTANCE_URL"].rstrip("/")
        token = os.environ["MASTODON_ACCESS_TOKEN"]
        try:
            res = post_form(f"{base}/api/v1/statuses", {"status": body},
                            {"Authorization": f"Bearer {token}"})
        except SocialHTTPError as exc:
            return SocialResult(platform=self.key, status="FAILED", message=f"Mastodon: {exc}")
        return SocialResult(platform=self.key, status="POSTED",
                            post_url=res.get("url") or res.get("uri"),
                            message="Posted to Mastodon.")
