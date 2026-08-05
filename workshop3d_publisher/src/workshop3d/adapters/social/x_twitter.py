"""X (Twitter) promo adapter (fully wired: OAuth 1.0a + POST /2/tweets).

Needs an X developer app with user-context keys (a normal account is not
enough). Secrets from env ONLY:
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
Note: X's free tier allows a limited number of posts per month.
"""
from __future__ import annotations

import os
import secrets
import time

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult
from ._nethttp import post_json, SocialHTTPError
from ._oauth1 import auth_header

_TWEETS_URL = "https://api.twitter.com/2/tweets"


@register_social
class XAdapter(SocialAdapter):
    key = "x"

    def credentials_present(self) -> bool:
        return all(os.environ.get(k) for k in
                   ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        # X posts cap at 280 characters.
        body = compose_post(record, "x", product_url)[:280]
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set X_API_KEY/SECRET and X_ACCESS_TOKEN/SECRET (developer app).")

        # OAuth 1.0a header. The JSON body does not participate in the signature.
        header = auth_header(
            "POST", _TWEETS_URL,
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            token=os.environ["X_ACCESS_TOKEN"],
            token_secret=os.environ["X_ACCESS_SECRET"],
            nonce=secrets.token_hex(16),
            timestamp=str(int(time.time())),
        )
        try:
            res = post_json(_TWEETS_URL, {"text": body}, {"Authorization": header})
        except SocialHTTPError as exc:
            return SocialResult(platform=self.key, status="FAILED", message=f"X: {exc}")
        tweet_id = (res.get("data") or {}).get("id", "")
        return SocialResult(platform=self.key, status="POSTED",
                            post_url=f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None,
                            message="Posted to X.")
