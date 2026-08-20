"""Configuration loading.

All settings live outside the code in config/config.yaml. Secrets are NEVER
stored here -- they are read from environment variables on demand by adapters.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Repo layout: <root>/config/config.yaml, this file at <root>/src/workshop3d/config.py
_PKG_DIR = Path(__file__).resolve().parent
_ROOT = _PKG_DIR.parent.parent
CONFIG_DIR = _ROOT / "config"
DEFAULT_CONFIG = CONFIG_DIR / "config.yaml"
EXAMPLE_CONFIG = CONFIG_DIR / "config.example.yaml"

_ZERO_TOUCH_STORES = (
    "cults3d",
    "thangs",
    "creality_cloud_eu",
    "creality_cloud_cn",
)

_ZERO_TOUCH_SOCIAL = (
    "facebook",
    "instagram",
    "x",
    "pinterest",
    "bluesky",
    "mastodon",
    "tiktok",
    "youtube",
)


class Config:
    """Thin, dotted-access wrapper around the parsed YAML config."""

    def __init__(self, data: dict[str, Any], source: Path | None = None):
        self._data = data
        self.source = source
        self._apply_mode_invariants()

    def _apply_mode_invariants(self) -> None:
        """Make the one-switch everyday mode authoritative."""
        if bool(self.get("modes.zero_touch", False)):
            self.set("modes.dry_run", False)
            self.set("modes.auto_publish", True)
            self.set("modes.require_approval", False)
            self.set("browser.auto_submit", True)
            # Rafał's daily workflow is fixed and intentionally has no setup
            # form: one product folder goes into the drop folder, is published
            # through the normal logged-in Chrome, then moved to the sibling
            # ``Opublikowane`` and pushed to the Nextcloud archive.  Google
            # Drive for desktop stays optional -- ``google_drive.enabled`` is
            # deliberately not forced here.
            self.set("cloud_sync.enabled", True)
            self.set("cloud_sync.mirror_enabled", True)
            self.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
            self.set("cloud_sync.published_folder", "Opublikowane")
            self.set("cloud_sync.google_drive.folder_name", "Folder Sync")
            self.set(
                "cloud_sync.google_drive.folder_id",
                "1bKkH3_P2XYCtFtSv4HlzmWE16cqjYGlo",
            )
            self.set(
                "cloud_sync.nextcloud.server_url",
                "https://cloud.workshop3d.pl",
            )
            self.set("cloud_sync.nextcloud.folder_path", "Folder Sync")
            # Always target the real web cloud.  An old empty local directory
            # must never masquerade as the Nextcloud destination.
            self.set("cloud_sync.nextcloud.prefer_webdav", True)
            self.set("cloud_sync.nextcloud.auto_connect", True)
            self.set("cloud_sync.nextcloud.local_folder", "")
            # Google Folder Sync jest obszarem roboczym i źródłem prawdy,
            # Nextcloud Folder Sync magazynem posprzedażowym: pliki lecą tylko
            # w jedną stronę, żeby archiwum nie odtwarzało sprzątniętych paczek.
            self.set("cloud_sync.mirror_direction", "google_to_nextcloud")
            self.set("cloud_sync.mirror_interval_seconds", 15)
            self.set("cloud_sync.process_existing_inbox", True)

            # The browser bridge discovers/reuses the matching open tab.  All
            # agreed store destinations therefore use browser mode and need no
            # API keys, staging paths or per-store switches in everyday mode.
            for store in _ZERO_TOUCH_STORES:
                self.set(f"stores.{store}.enabled", True)
                self.set(f"stores.{store}.mode", "browser")
                self.set(f"stores.{store}.publish_as", "public")
            for network in _ZERO_TOUCH_SOCIAL:
                self.set(f"social.{network}.enabled", True)
                self.set(f"social.{network}.mode", "browser")

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "Config":
        """Load config.yaml, falling back to config.example.yaml on first run."""
        chosen = Path(path) if path else DEFAULT_CONFIG
        if not chosen.exists():
            if EXAMPLE_CONFIG.exists():
                chosen = EXAMPLE_CONFIG
            else:
                raise FileNotFoundError(
                    f"No config found at {DEFAULT_CONFIG} or {EXAMPLE_CONFIG}"
                )
        with open(chosen, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(data, source=chosen)

    def reload(self) -> None:
        """Re-read the source file in place so live objects see new settings."""
        if self.source and Path(self.source).exists():
            with open(self.source, "r", encoding="utf-8") as fh:
                self._data = yaml.safe_load(fh) or {}
            self._apply_mode_invariants()

    def save(self, data: dict | None = None) -> None:
        """Write config back to config.yaml (creating it if we were on example).

        Never writes to the example file -- always the real config.yaml.
        """
        if data is not None:
            self._data = data
        self._apply_mode_invariants()
        target = DEFAULT_CONFIG
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self._data, fh, allow_unicode=True, sort_keys=False)
        self.source = target

    def set(self, dotted: str, value: Any) -> None:
        node = self._data
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    # Convenience accessors -------------------------------------------------
    @property
    def ready_folder(self) -> Path:
        return Path(self.get("paths.ready_folder", "Gotowe do sklepu"))

    @property
    def work_folder(self) -> Path:
        return Path(self.get("paths.work_folder", "work"))

    @property
    def dry_run(self) -> bool:
        # Safe default: DRY_RUN on.
        return bool(self.get("modes.dry_run", True))

    @property
    def auto_publish(self) -> bool:
        return bool(self.get("modes.auto_publish", False))

    @property
    def zero_touch(self) -> bool:
        return (
            not self.dry_run
            and self.auto_publish
            and not bool(self.get("modes.require_approval", True))
            and bool(self.get("browser.auto_submit", False))
        )

    def enabled_stores(self) -> dict[str, dict]:
        stores = self.get("stores", {}) or {}
        return {k: v for k, v in stores.items() if v and v.get("enabled")}

    def enabled_social(self) -> dict[str, dict]:
        social = self.get("social", {}) or {}
        return {
            k: v
            for k, v in social.items()
            if isinstance(v, dict) and v.get("enabled")
        }

    def resolve_path(self, dotted: str, default: str = "") -> Path | None:
        """Resolve a user-configured asset path against the application root."""
        raw = str(self.get(dotted, default) or "").strip()
        if not raw:
            return None
        path = Path(raw).expanduser()
        return path if path.is_absolute() else (_ROOT / path)

    @property
    def raw(self) -> dict:
        return self._data
