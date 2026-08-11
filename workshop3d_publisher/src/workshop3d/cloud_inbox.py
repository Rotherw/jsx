"""Watch Google FolderSync/Gotowe do sklepu as the publishing inbox.

On first connection all folders already present are recorded as a baseline and
are *not* republished.  Afterwards a new or changed top-level product folder is
handed to the normal pipeline once Google Drive has finished copying it.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Callable

from . import cloud_sync
from .folder_watcher import has_pending_temp_files, has_required_files, is_stable


class CloudInboxWatcher:
    def __init__(
        self,
        config,
        on_ready: Callable[[Path], None],
        enabled: Callable[[], bool] | None = None,
        state_path: str | Path | None = None,
    ):
        self.config = config
        self.on_ready = on_ready
        self.enabled = enabled or (lambda: True)
        self.ignore = config.get("trigger.ignore_patterns", []) or []
        self.state_path = (
            Path(state_path)
            if state_path is not None
            else config.work_folder / "cloud_inbox_state.json"
        )
        self.state = _load(self.state_path)
        if not self.state:
            self.state = {
                "baseline_complete": False,
                "folders": {},
                "processed_count": 0,
                "last_product_at": None,
            }
            _save(self.state_path, self.state)

    def poll_once(self, now: Callable[[], float] = time.time) -> dict:
        if not self.enabled():
            return self.state

        inbox = cloud_sync.discover_google_inbox(self.config)
        stamp = float(now())
        if inbox is None:
            self.state.update(
                {
                    "status": "WAITING",
                    "google_inbox": None,
                    "last_scan_at": stamp,
                    "message": "Czekam na Google FolderSync/Gotowe do sklepu.",
                }
            )
            _save(self.state_path, self.state)
            return self.state

        folders = [
            folder
            for folder in sorted(inbox.iterdir())
            if folder.is_dir()
            and folder.name.strip()
            and not folder.name.startswith(".workshop3d-syncing-")
        ]
        previous_inbox = self.state.get("google_inbox")
        if previous_inbox and os.path.normcase(str(previous_inbox)) != os.path.normcase(str(inbox)):
            # A remounted drive letter or a changed account must be baselined
            # again; its historical folders are not a new publication queue.
            self.state["baseline_complete"] = False
            self.state["folders"] = {}
        known = self.state.setdefault("folders", {})

        # Safety on installation/update: do not treat the user's historical
        # cloud archive as a queue of products waiting to be republished.
        if not self.state.get("baseline_complete"):
            for folder in folders:
                signature = _signature(folder, self.ignore)
                known[folder.name] = {
                    "observed_signature": signature,
                    "handled_signature": signature,
                    "changed_at": stamp,
                    "handled_at": stamp,
                }
            self.state.update(
                {
                    "baseline_complete": True,
                    "status": "WATCHING",
                    "google_inbox": str(inbox),
                    "last_scan_at": stamp,
                    "message": (
                        f"Zapamiętano {len(folders)} istniejących folderów. "
                        "Czekam na nowy gotowy produkt."
                    ),
                }
            )
            _save(self.state_path, self.state)
            return self.state

        delay = float(self.config.get("trigger.stability_delay_seconds", 60))
        checks = max(1, int(self.config.get("trigger.stability_checks", 3)))
        interval = max(0.0, float(self.config.get("trigger.seconds_between_checks", 5)))
        present = {folder.name for folder in folders}

        for folder in folders:
            signature = _signature(folder, self.ignore)
            info = known.get(folder.name)
            if info is None:
                known[folder.name] = {
                    "observed_signature": signature,
                    "handled_signature": None,
                    "changed_at": stamp,
                    "handled_at": None,
                }
                continue

            info["present"] = True
            if signature == info.get("handled_signature"):
                info["observed_signature"] = signature
                continue
            if signature != info.get("observed_signature"):
                info["observed_signature"] = signature
                info["changed_at"] = stamp
                continue
            if stamp - float(info.get("changed_at", stamp)) < delay:
                continue
            if not signature or not has_required_files(folder):
                continue
            if has_pending_temp_files(folder, self.ignore):
                continue
            if not is_stable(
                folder,
                self.ignore,
                checks=checks,
                interval=interval,
            ):
                continue
            if not self.enabled():
                break

            self.on_ready(folder)
            # Only mark it handled after the pipeline accepted the call.  A
            # crash or exception therefore causes a safe automatic retry.
            info["handled_signature"] = signature
            info["handled_at"] = time.time()
            self.state["processed_count"] = int(
                self.state.get("processed_count", 0)
            ) + 1
            self.state["last_product_at"] = info["handled_at"]

        for name, info in known.items():
            info["present"] = name in present

        self.state.update(
            {
                "status": "WATCHING",
                "google_inbox": str(inbox),
                "last_scan_at": stamp,
                "message": (
                    "Nasłuchuję Google FolderSync/Gotowe do sklepu. "
                    f"Uruchomiono produktów: {self.state.get('processed_count', 0)}."
                ),
            }
        )
        _save(self.state_path, self.state)
        return self.state

    def run_forever(self, poll_interval: float = 10.0) -> None:  # pragma: no cover
        while True:
            try:
                self.poll_once()
            except Exception as exc:
                self.state["status"] = "ERROR"
                self.state["message"] = f"Błąd skrzynki Google: {exc}"
                try:
                    _save(self.state_path, self.state)
                except OSError:
                    pass
                print(f"[cloud-inbox] error: {exc}")
            time.sleep(max(poll_interval, 2))


def read_status(config) -> dict:
    return _load(config.work_folder / "cloud_inbox_state.json")


def _signature(folder: Path, ignore: list[str]) -> str:
    digest = hashlib.sha256()
    found = False
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in ignore):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        found = True
        digest.update(path.relative_to(folder).as_posix().encode("utf-8"))
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest() if found else ""


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)
