"""Publication orchestration across store & social adapters (spec 14-16).

Guarantees:
  * idempotency -- a platform already PUBLISHED/POSTED is never re-published;
  * failure isolation -- one platform failing never stops the others;
  * promotion runs only after >=1 store listing exists with a real URL.
"""
from __future__ import annotations

from .config import Config
from .models import ProductRecord, StoreResult, SocialResult
from . import adapters


def publish_stores(record: ProductRecord, config: Config, workspace: str) -> None:
    for key, settings in config.enabled_stores().items():
        existing = record.stores.get(key)
        # Idempotency: skip anything already live.
        if existing and existing.get("status") == "PUBLISHED":
            continue
        adapter = adapters.get_store_adapter(key, config, settings)
        if adapter is None:
            record.stores[key] = StoreResult(platform=key, status="FAILED",
                                             message="No adapter registered.").__dict__
            continue
        try:
            result = adapter.publish(record, workspace)
        except Exception as exc:  # isolation: never propagate
            result = StoreResult(platform=key, status="FAILED", message=str(exc))
            record.error_history.append(f"[{key}] {exc}")
        record.stores[key] = result.__dict__


def has_live_listing(record: ProductRecord) -> bool:
    return any(
        r.get("status") in ("PUBLISHED", "DRY_RUN") and r.get("url")
        for r in record.stores.values()
    )


def main_product_url(record: ProductRecord, config: Config) -> str | None:
    for platform in config.get("links.main_link_priority", []) or []:
        r = record.stores.get(platform)
        if r and r.get("url") and r.get("status") in ("PUBLISHED", "DRY_RUN"):
            return r["url"]
    for r in record.stores.values():
        if r.get("url") and r.get("status") in ("PUBLISHED", "DRY_RUN"):
            return r["url"]
    return None


def promote_social(record: ProductRecord, config: Config, workspace: str) -> None:
    # Promotion only after a successful store listing with a real URL.
    if not has_live_listing(record):
        return
    product_url = main_product_url(record, config) or ""

    for key, settings in config.enabled_social().items():
        existing = record.social.get(key)
        if existing and existing.get("status") == "POSTED":
            continue
        adapter = adapters.get_social_adapter(key, config, settings)
        if adapter is None:
            record.social[key] = SocialResult(platform=key, status="FAILED",
                                              message="No adapter registered.").__dict__
            continue
        try:
            result = adapter.post(record, product_url, workspace)
        except Exception as exc:
            result = SocialResult(platform=key, status="FAILED", message=str(exc))
            record.error_history.append(f"[{key}] {exc}")
        record.social[key] = result.__dict__
