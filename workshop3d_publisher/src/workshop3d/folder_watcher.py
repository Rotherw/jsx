"""Folder monitoring (spec section 3).

Detects new product folders in "Gotowe do sklepu", waits for copying to finish
(size-stability check + safety delay), ignores temp/partial files, and only
then hands the folder to the pipeline.

Works in two ways:
  * poll-based scanning (always available, used by tests);
  * watchdog observer (optional real-time trigger).
"""
from __future__ import annotations

import fnmatch
import time
from pathlib import Path
from typing import Callable

from .config import Config


def is_ignored(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def folder_snapshot(folder: Path, ignore: list[str]) -> dict[str, int]:
    """Map of relative file path -> size, skipping ignored/temp files."""
    snap: dict[str, int] = {}
    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        if is_ignored(p.name, ignore):
            continue
        try:
            snap[str(p.relative_to(folder))] = p.stat().st_size
        except OSError:
            pass
    return snap


def has_pending_temp_files(folder: Path, ignore: list[str]) -> bool:
    for p in folder.rglob("*"):
        if p.is_file() and is_ignored(p.name, ignore):
            return True
    return False


def is_stable(
    folder: Path,
    ignore: list[str],
    checks: int = 3,
    interval: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """True when the file-size snapshot is identical across `checks` reads."""
    prev = folder_snapshot(folder, ignore)
    stable_count = 1
    while stable_count < checks:
        sleep(interval)
        current = folder_snapshot(folder, ignore)
        if current == prev and current:
            stable_count += 1
        else:
            stable_count = 1
            prev = current
    return bool(prev)


def has_required_files(folder: Path) -> bool:
    has_png = any(p.suffix.lower() == ".png" for p in folder.rglob("*") if p.is_file())
    has_stl = any(p.suffix.lower() == ".stl" for p in folder.rglob("*") if p.is_file())
    return has_png and has_stl


def scan_ready_folder(config: Config) -> list[Path]:
    """Return product sub-folders currently present in the ready folder."""
    ready = config.ready_folder
    if not ready.exists():
        return []
    return [p for p in sorted(ready.iterdir()) if p.is_dir() and p.name.strip()]


class Watcher:
    """Optional real-time observer (watchdog). Falls back to polling if absent."""

    def __init__(self, config: Config, on_ready: Callable[[Path], None]):
        self.config = config
        self.on_ready = on_ready
        self.ignore = config.get("trigger.ignore_patterns", []) or []
        self._last_change: dict[str, float] = {}

    def poll_once(self, now: Callable[[], float] = time.time) -> None:
        """One polling pass: process folders that are stable & complete."""
        delay = float(self.config.get("trigger.stability_delay_seconds", 60))
        checks = int(self.config.get("trigger.stability_checks", 3))
        interval = float(self.config.get("trigger.seconds_between_checks", 5))

        for folder in scan_ready_folder(self.config):
            snap = folder_snapshot(folder, self.ignore)
            key = folder.name
            signature = hash(tuple(sorted(snap.items())))
            marker = self._last_change.get(key)
            if marker is None or marker != signature:
                # Folder changed since last pass -> reset the safety timer.
                self._last_change[key] = signature
                self._last_change[key + "@t"] = now()  # type: ignore[assignment]
                continue
            # Unchanged: has the safety delay elapsed?
            since = now() - float(self._last_change.get(key + "@t", now()))  # type: ignore[arg-type]
            if since < delay:
                continue
            if has_pending_temp_files(folder, self.ignore):
                continue
            if not is_stable(folder, self.ignore, checks=checks, interval=interval):
                continue
            self.on_ready(folder)

    def run_forever(self, poll_interval: float = 10.0) -> None:  # pragma: no cover
        """Blocking loop for production use."""
        while True:
            try:
                self.poll_once()
            except Exception as exc:
                print(f"[watcher] error: {exc}")
            time.sleep(poll_interval)
