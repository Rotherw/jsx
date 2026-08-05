"""X (Twitter) promo adapter.

Posting to X requires an approved developer app with OAuth 1.0a / OAuth 2.0
user context -- there is no simple token-only path. This adapter prepares the
post and stops honestly at NOT_CONNECTED / a marked connection point rather
than faking a tweet. Secrets from env ONLY (when wired):
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult


@register_social
class XAdapter(SocialAdapter):
    key = "x"

    def credentials_present(self) -> bool:
        return bool(
            os.environ.get("X_API_KEY") and os.environ.get("X_API_SECRET")
            and os.environ.get("X_ACCESS_TOKEN") and os.environ.get("X_ACCESS_SECRET")
        )

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        body = compose_post(record, "x", product_url)
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="X needs a developer app (X_API_KEY/SECRET + ACCESS_TOKEN/SECRET).")
        try:
            raise NotImplementedError(
                "X posting needs OAuth 1.0a signing of POST /2/tweets. Not wired yet; see README."
            )
        except Exception as exc:
            return SocialResult(platform=self.key, status="FAILED", message=str(exc))
