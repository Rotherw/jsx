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


class Config:
    """Thin, dotted-access wrapper around the parsed YAML config."""

    def __init__(self, data: dict[str, Any], source: Path | None = None):
        self._data = data
        self.source = source

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

    @property
    def raw(self) -> dict:
        return self._data
