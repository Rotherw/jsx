"""Bluesky promo adapter (fully wired, AT Protocol).

Secrets from env ONLY:
    BLUESKY_HANDLE        (e.g. workshop3d.bsky.social)
    BLUESKY_APP_PASSWORD  (Settings -> App Passwords)

Flow: createSession -> createRecord (app.bsky.feed.post).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult
from ._nethttp import post_json, SocialHTTPError

_PDS = "https://bsky.social"


@register_social
class BlueskyAdapter(SocialAdapter):
    key = "bluesky"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("BLUESKY_HANDLE") and os.environ.get("BLUESKY_APP_PASSWORD"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        # Bluesky posts cap at 300 characters.
        body = compose_post(record, "bluesky", product_url)[:300]
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN post prepared:\n{body}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD.")
        handle = os.environ["BLUESKY_HANDLE"]
        password = os.environ["BLUESKY_APP_PASSWORD"]
        try:
            session = post_json(f"{_PDS}/xrpc/com.atproto.server.createSession",
                                {"identifier": handle, "password": password})
            jwt = session["accessJwt"]
            did = session["did"]
            created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            record_body = {
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {"$type": "app.bsky.feed.post", "text": body, "createdAt": created},
            }
            res = post_json(f"{_PDS}/xrpc/com.atproto.repo.createRecord", record_body,
                            {"Authorization": f"Bearer {jwt}"})
        except SocialHTTPError as exc:
            return SocialResult(platform=self.key, status="FAILED", message=f"Bluesky: {exc}")
        except KeyError:
            return SocialResult(platform=self.key, status="FAILED",
                                message="Bluesky: unexpected session response.")
        rkey = str(res.get("uri", "")).rsplit("/", 1)[-1]
        url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else None
        return SocialResult(platform=self.key, status="POSTED", post_url=url,
                            message="Posted to Bluesky.")
