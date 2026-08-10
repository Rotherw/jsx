"""Asset-host contract + registry.

Some stores (notably Cults3D) do not accept file uploads; they reference
images and 3D files by public HTTPS URL. An AssetHost turns local product
files into public URLs. Hosts are decoupled and self-registering, exactly like
store/social adapters, so a new host is one file.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class AssetHostError(Exception):
    """Raised when public URLs cannot be produced (message is user-facing)."""


class AssetHost(ABC):
    key: str = ""

    def __init__(self, config, settings: dict):
        self.config = config
        self.settings = settings or {}

    @abstractmethod
    def host(self, product_id: str, paths: list[Path]) -> dict[str, str]:
        """Return {local_filename: public_url} for each path, hosting as needed.

        Must be idempotent: hosting the same product/file twice returns the
        same URL and never creates a duplicate.
        """


_HOSTS: dict[str, type[AssetHost]] = {}


def register_host(cls: type[AssetHost]) -> type[AssetHost]:
    _HOSTS[cls.key] = cls
    return cls


def get_asset_host(key: str, config, override_settings: dict | None = None) -> AssetHost | None:
    cls = _HOSTS.get(key)
    if cls is None:
        return None
    settings = dict(config.get(f"asset_hosts.{key}", {}) or {})
    if override_settings:
        settings.update({k: v for k, v in override_settings.items() if v is not None})
    return cls(config, settings)
