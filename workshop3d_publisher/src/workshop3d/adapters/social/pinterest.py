"""Pinterest promo adapter (fully wired to the API v5).

Creates a Pin with the product link and the hosted cover image. Needs a
Pinterest developer app access token + a target board id (a normal account is
not enough). Secrets from env ONLY:
    PINTEREST_ACCESS_TOKEN, PINTEREST_BOARD_ID
"""
from __future__ import annotations

import os

from ..base import SocialAdapter, register_social, compose_post
from ...models import ProductRecord, SocialResult
from ._nethttp import post_json, SocialHTTPError
from ._media import hosted_cover_url

_API = "https://api.pinterest.com/v5"


@register_social
class PinterestAdapter(SocialAdapter):
    key = "pinterest"

    def credentials_present(self) -> bool:
        return bool(os.environ.get("PINTEREST_ACCESS_TOKEN") and os.environ.get("PINTEREST_BOARD_ID"))

    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        description = compose_post(record, "pinterest", product_url)
        title = record.metadata.get("TITLE", record.folder_name)[:100]
        if self.config.dry_run:
            return SocialResult(platform=self.key, status="DRY_RUN",
                                message=f"DRY_RUN pin prepared:\n{description}")
        if not self.credentials_present():
            return SocialResult(platform=self.key, status="NOT_CONNECTED",
                                message="Set PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID.")

        image_url = hosted_cover_url(record, self.config, workspace)
        if not image_url:
            return SocialResult(platform=self.key, status="NEEDS_ATTENTION",
                                message="Pinterest needs a public image URL. Configure the Google Drive asset host.")

        token = os.environ["PINTEREST_ACCESS_TOKEN"]
        pin = {
            "board_id": os.environ["PINTEREST_BOARD_ID"],
            "title": title,
            "description": description,
            "link": product_url or None,
            "media_source": {"source_type": "image_url", "url": image_url},
        }
        try:
            res = post_json(f"{_API}/pins", pin, {"Authorization": f"Bearer {token}"})
        except SocialHTTPError as exc:
            return SocialResult(platform=self.key, status="FAILED", message=f"Pinterest: {exc}")
        pin_id = res.get("id", "")
        return SocialResult(platform=self.key, status="POSTED",
                            post_url=f"https://www.pinterest.com/pin/{pin_id}" if pin_id else None,
                            message="Posted to Pinterest.")
