"""Cults3D store adapter (live GraphQL publishing).

Secrets from the environment ONLY:
    CULTS3D_API_USER, CULTS3D_API_KEY

Behaviour (honest, never fakes a publish):
  * DRY_RUN              -> simulates, returns a preview URL, no network call.
  * no credentials       -> NOT_CONNECTED.
  * assets not hostable  -> NEEDS_ATTENTION (Cults3D needs public HTTPS URLs).
  * ready + AUTO_PUBLISH -> real createCreation mutation; returns id + url.

Cults3D asset model: files/images are referenced by public HTTPS URLs, not
uploaded. Set `stores.cults3d.asset_base_url` in config to a location where the
product's work files are publicly reachable. Without it the adapter stops this
one listing and tells you exactly which files to host.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..base import StoreAdapter, register_store
from ...models import ProductRecord, StoreResult
from ...text_utils import slugify
from ._cults_api import Cults3DClient, Cults3DError


@register_store
class Cults3DAdapter(StoreAdapter):
    key = "cults3d"
    supports_formats = ("stl", "3mf", "glb")

    def credentials_present(self) -> bool:
        return bool(os.environ.get("CULTS3D_API_USER") and os.environ.get("CULTS3D_API_KEY"))

    # -- main entry ---------------------------------------------------------
    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        meta = record.metadata
        title = meta.get("TITLE", record.folder_name)

        if self.config.dry_run:
            slug = meta.get("SLUG", slugify(title))
            return StoreResult(
                platform=self.key, status="DRY_RUN",
                url=f"https://cults3d.com/en/3d-model/{slug}",
                message="DRY_RUN: listing prepared, not published.",
            )

        if not self.credentials_present():
            return StoreResult(
                platform=self.key, status="NOT_CONNECTED",
                message="Set CULTS3D_API_USER and CULTS3D_API_KEY to enable publishing.",
            )

        # Resolve public asset URLs (Cults3D requirement).
        try:
            image_urls, file_urls = self._resolve_assets(record, workspace)
        except _AssetsNotHostable as exc:
            return StoreResult(platform=self.key, status="NEEDS_ATTENTION", message=str(exc))

        try:
            return self._publish_via_api(record, title, image_urls, file_urls)
        except Cults3DError as exc:
            return StoreResult(platform=self.key, status="FAILED", message=f"Cults3D: {exc}")

    # -- asset URLs ---------------------------------------------------------
    def _resolve_assets(self, record: ProductRecord, workspace: str) -> tuple[list[str], list[str]]:
        from ...asset_hosts import get_asset_host, AssetHostError

        max_files = int(self.settings.get("max_files", 10))

        # Explicit per-record URLs (advanced users) win if provided in metadata.
        explicit = record.metadata.get("CULTS3D_ASSET_URLS")
        if explicit:
            return (explicit.get("images", [])[:max_files],
                    explicit.get("files", [])[:max_files])

        # Pick which local files to host: images (PNG) + model files. Cults3D
        # recommends hosting a ZIP for the model, which the pipeline builds.
        base = Path(workspace)
        media_dir, files_dir, package_dir = base / "media", base / "files", base / "package"
        images = sorted(media_dir.glob("*.png")) if media_dir.exists() else []
        if not images and files_dir.exists():
            images = sorted(files_dir.glob("*.png"))

        model_exts = (".stl", ".3mf", ".glb", ".zip")
        if self.settings.get("file_selection", "zip") == "zip" and package_dir.exists():
            model_paths = sorted(package_dir.glob("*.zip"))
        else:
            model_paths = []
        if not model_paths and files_dir.exists():
            model_paths = [p for p in sorted(files_dir.glob("*")) if p.suffix.lower() in model_exts]

        images = images[:max_files]
        model_paths = model_paths[:max_files]
        if not images or not model_paths:
            raise _AssetsNotHostable("No images or model files found to host for Cults3D.")

        # Resolve to public URLs via the configured asset host.
        host_key = self.settings.get("asset_host", "static")
        override = {"base_url": self.settings.get("asset_base_url")} if host_key == "static" else None
        host = get_asset_host(host_key, self.config, override)
        if host is None:
            raise _AssetsNotHostable(f"Unknown asset_host '{host_key}'. Use 'google_drive' or 'static'.")
        try:
            image_urls = list(host.host(record.product_id, images).values())
            file_urls = list(host.host(record.product_id, model_paths).values())
        except AssetHostError as exc:
            raise _AssetsNotHostable(str(exc))
        return image_urls, file_urls

    # -- live publish -------------------------------------------------------
    def _publish_via_api(self, record: ProductRecord, title: str,
                        image_urls: list[str], file_urls: list[str]) -> StoreResult:
        meta = record.metadata
        client = Cults3DClient(
            os.environ["CULTS3D_API_USER"], os.environ["CULTS3D_API_KEY"],
        )

        locale = str(self.settings.get("locale", "EN"))
        currency = str(meta.get("PRICE", {}).get("currency", "USD"))
        amount = float(meta.get("PRICE", {}).get("amount", 0.0) or 0.0)
        if self.settings.get("price_in_cents"):
            amount = round(amount * 100)
        category_id = self._category_id(client, meta.get("CATEGORY"), locale)
        license_code = self.settings.get("license_code") or None
        tags = meta.get("TAGS", [])[: int(self.settings.get("max_tags", 20))]

        result = client.create_creation(
            name=title,
            description=meta.get("DESCRIPTION_EN", ""),
            image_urls=image_urls, file_urls=file_urls,
            locale=locale, currency=currency,
            download_price=amount, category_id=category_id,
            license_code=license_code, tag_names=tags,
        )
        return StoreResult(
            platform=self.key, status="PUBLISHED",
            listing_id=result.id, url=result.url,
            message="Created on Cults3D (verify/finalise in your Cults dashboard).",
        )

    def _category_id(self, client: Cults3DClient, category_name, locale: str) -> str | None:
        # Explicit override wins.
        forced = self.settings.get("category_id")
        if forced:
            return str(forced)
        if not category_name:
            return None
        try:
            cats = client.list_categories(locale)
        except Cults3DError:
            return None
        target = str(category_name).strip().lower()
        for c in cats:
            if str(c.get("name", "")).strip().lower() == target:
                return str(c.get("id"))
        # Partial match fallback (e.g. our "terrain" -> "Terrains").
        for c in cats:
            if target in str(c.get("name", "")).strip().lower():
                return str(c.get("id"))
        return None


class _AssetsNotHostable(Exception):
    """Raised when Cults3D-required public asset URLs cannot be produced."""
