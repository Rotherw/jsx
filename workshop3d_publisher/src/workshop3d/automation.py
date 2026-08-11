"""Runtime switch for the folder automation.

The dashboard and watcher share this object.  Keeping the switch outside of
Flask means that pressing "pause" really stops new folders from being handed
to the pipeline instead of merely changing a label in the web page.
"""
from __future__ import annotations

import threading


class AutomationControl:
    """Small thread-safe start/pause switch."""

    def __init__(self, enabled: bool = True):
        self._enabled = bool(enabled)
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> bool:
        with self._lock:
            self._enabled = bool(enabled)
            return self._enabled

    def toggle(self) -> bool:
        with self._lock:
            self._enabled = not self._enabled
            return self._enabled
