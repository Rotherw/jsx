"""Adapter contracts + registries (spec sections 14, 16, 22).

Store and social adapters are decoupled from the core logic. Adding a new
platform = adding one file that registers itself; no core rebuild required.

Publishing rules honoured by every adapter:
  * DRY_RUN never touches an external service -> status "DRY_RUN".
  * Missing credentials/session -> status "NOT_CONNECTED" (never a fake success).
  * A failing adapter must not stop the others (handled by the manager).
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Callable

from ..config import Config
from ..models import ProductRecord, StoreResult, SocialResult


class StoreAdapter(ABC):
    """One sales platform (Cults3D, Thangs, Creality, ...)."""

    #: unique key that must match the config `stores.<key>` block
    key: str = ""
    #: which extra formats besides STL this platform can host inline
    supports_formats: tuple[str, ...] = ("stl",)

    def __init__(self, config: Config, settings: dict):
        self.config = config
        self.settings = settings or {}

    def credentials_present(self) -> bool:
        """Override to check env vars / session. Default: not connected."""
        return False

    @abstractmethod
    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        """Publish (or simulate) the listing and return a StoreResult."""


class SocialAdapter(ABC):
    """One social platform (Facebook, Instagram, TikTok, YouTube)."""

    key: str = ""

    def __init__(self, config: Config, settings: dict):
        self.config = config
        self.settings = settings or {}

    def credentials_present(self) -> bool:
        return False

    @abstractmethod
    def post(self, record: ProductRecord, product_url: str, workspace: str) -> SocialResult:
        """Publish (or simulate) a promo post and return a SocialResult."""


# --- registries --------------------------------------------------------------
_STORES: dict[str, type[StoreAdapter]] = {}
_SOCIAL: dict[str, type[SocialAdapter]] = {}


def register_store(cls: type[StoreAdapter]) -> type[StoreAdapter]:
    _STORES[cls.key] = cls
    return cls


def register_social(cls: type[SocialAdapter]) -> type[SocialAdapter]:
    _SOCIAL[cls.key] = cls
    return cls


def get_store_adapter(key: str, config: Config, settings: dict) -> StoreAdapter | None:
    cls = _STORES.get(key)
    return cls(config, settings) if cls else None


def get_social_adapter(key: str, config: Config, settings: dict) -> SocialAdapter | None:
    cls = _SOCIAL.get(key)
    return cls(config, settings) if cls else None


def _env(name: str) -> str | None:
    val = os.environ.get(name)
    return val if val else None
