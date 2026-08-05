"""Shared helper: turn a product's cover image into a public URL.

Instagram and Pinterest require a publicly reachable image URL. We reuse the
same asset-host layer as the Cults3D store (Google Drive by default), so the
cover the pipeline already rendered is hosted and linked.
"""
from __future__ import annotations

from pathlib import Path


def hosted_cover_url(record, config, workspace: str) -> str | None:
    media = Path(workspace) / "media"
    images = sorted(media.glob("*.png")) if media.exists() else []
    if not images:
        files = Path(workspace) / "files"
        images = sorted(files.glob("*.png")) if files.exists() else []
    if not images:
        return None

    # Prefer a square frame if present (best for IG/Pinterest).
    preferred = next((p for p in images if "square" in p.name or "cover" in p.name), images[0])

    from ...asset_hosts import get_asset_host, AssetHostError
    host_key = config.get("social.image_host", "google_drive")
    host = get_asset_host(host_key, config)
    if host is None:
        return None
    try:
        urls = host.host(record.product_id, [preferred])
    except AssetHostError:
        return None
    return next(iter(urls.values()), None)
