"""Central product link card (spec section 17)."""
from __future__ import annotations

from .config import Config
from .models import ProductRecord


def build_link_card(record: ProductRecord, config: Config) -> tuple[dict[str, str], str | None]:
    """Collect all working links and pick the main one by configured priority.

    Only real, successful links are included (DRY_RUN preview links count as
    links so the dashboard is useful during testing, but PUBLISHED wins).
    """
    links: dict[str, str] = {}
    for platform, result in record.stores.items():
        url = result.get("url")
        if url and result.get("status") in ("PUBLISHED", "DRY_RUN"):
            links[platform] = url
    for platform, result in record.social.items():
        url = result.get("post_url")
        if url and result.get("status") in ("POSTED", "DRY_RUN"):
            links[platform] = url

    main_link = None
    for platform in config.get("links.main_link_priority", []) or []:
        if platform in links:
            main_link = links[platform]
            break
    if main_link is None and links:
        main_link = next(iter(links.values()))

    return links, main_link
