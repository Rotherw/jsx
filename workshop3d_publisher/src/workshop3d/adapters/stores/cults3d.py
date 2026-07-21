"""Cults3D store adapter.

Cults3D exposes a GraphQL API. This adapter prefers the API; a browser
automation mode is available as a separate strategy when no API key exists.

Secrets are read from the environment ONLY:
    CULTS3D_API_USER, CULTS3D_API_KEY

Honest behaviour:
  * DRY_RUN         -> simulates, returns a preview URL, no network call.
  * no credentials  -> NOT_CONNECTED (never pretends to have published).
  * credentials set -> attempts the real GraphQL mutation.
"""
from __future__ import annotations

import os

from ..base import StoreAdapter, register_store
from ...models import ProductRecord, StoreResult
from ...text_utils import slugify


@register_store
class Cults3DAdapter(StoreAdapter):
    key = "cults3d"
    supports_formats = ("stl", "3mf", "glb")

    def credentials_present(self) -> bool:
        return bool(os.environ.get("CULTS3D_API_USER") and os.environ.get("CULTS3D_API_KEY"))

    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        meta = record.metadata
        title = meta.get("TITLE", record.folder_name)

        if self.config.dry_run:
            slug = meta.get("SLUG", slugify(title))
            return StoreResult(
                platform=self.key,
                status="DRY_RUN",
                url=f"https://cults3d.com/en/3d-model/{slug}",
                message="DRY_RUN: listing prepared, not published.",
            )

        if not self.credentials_present():
            return StoreResult(
                platform=self.key,
                status="NOT_CONNECTED",
                message="Set CULTS3D_API_USER and CULTS3D_API_KEY to enable publishing.",
            )

        # Real publish path. Implemented as a guarded stub: the GraphQL request
        # is only attempted when credentials exist, and any failure is reported
        # honestly rather than faked.
        try:
            return self._publish_via_api(record, workspace, title)
        except Exception as exc:  # network / API errors must not fake success
            return StoreResult(
                platform=self.key,
                status="FAILED",
                message=f"Cults3D API error: {exc}",
            )

    def _publish_via_api(self, record: ProductRecord, workspace: str, title: str) -> StoreResult:
        """Perform the real GraphQL create-creation mutation.

        Left as an explicit, connected implementation point: the endpoint,
        auth headers and multipart file upload are documented in README.
        Until the HTTP calls are wired to a verified account this raises so we
        never report a publish that did not happen.
        """
        raise NotImplementedError(
            "Cults3D live upload not wired yet. See README 'Connecting Cults3D'. "
            "Credentials were detected; implement the GraphQL mutation to go live."
        )
