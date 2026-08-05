"""Static base-URL asset host.

For users who mirror the work directory to their own public web space. Builds
URLs as <base_url>/<product_id>/<filename>. Uploads nothing -- the user is
responsible for making those files reachable.
"""
from __future__ import annotations

from pathlib import Path

from .base import AssetHost, AssetHostError, register_host


@register_host
class StaticBaseUrlHost(AssetHost):
    key = "static"

    def host(self, product_id: str, paths: list[Path]) -> dict[str, str]:
        base = (self.settings.get("base_url") or "").rstrip("/")
        if not base:
            raise AssetHostError(
                "Cults3D needs public HTTPS links to your files. Either set a "
                "Google Drive asset host, or set asset_hosts.static.base_url "
                "(or stores.cults3d.asset_base_url) to a public location that "
                "mirrors the product's work folder."
            )
        return {p.name: f"{base}/{product_id}/{p.name}" for p in paths}
