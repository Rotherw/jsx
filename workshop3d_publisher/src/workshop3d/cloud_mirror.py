"""Non-destructive two-way mirror between Google and Nextcloud Folder Sync.

New and changed files under ``Gotowe do sklepu`` and ``Opublikowane`` flow both
ways. Deletions are deliberately not mirrored: if a file disappears from one
side, the surviving copy restores it. If both sides changed the same relative
path, the newer file becomes the common file; no duplicate product or conflict
folders are created. The explicit completed-product move is handled atomically
by :mod:`cloud_sync` on both roots, outside this generic deletion rule.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from . import cloud_sync

_IGNORE_SUFFIXES = (".tmp", ".part", ".crdownload")


def sync_once(config, state_path: str | Path | None = None) -> dict:
    with cloud_sync.SYNC_LOCK:
        return _sync_once_unlocked(config, state_path)


def _sync_once_unlocked(config, state_path: str | Path | None = None) -> dict:
    google = cloud_sync.discover_google_folder(config)
    nextcloud = cloud_sync.discover_nextcloud_folder(config)
    synced_folders = {
        cloud_sync.inbox_name(config),
        cloud_sync.published_name(config),
    }
    path = Path(state_path) if state_path else config.work_folder / "cloud_mirror_state.json"
    previous = _load(path)

    if google is None or nextcloud is None:
        status = {
            "status": "WAITING",
            "google_folder": str(google) if google else None,
            "nextcloud_folder": str(nextcloud) if nextcloud else None,
            "last_sync_at": previous.get("last_sync_at"),
            "copied_google_to_nextcloud": 0,
            "copied_nextcloud_to_google": 0,
            "conflicts": 0,
            "message": (
                "Czekam na lokalne FolderSync Google i Folder Sync Nextcloud."
            ),
            "files": previous.get("files", {}),
        }
        _save(path, status)
        return status

    old_files = previous.get("files", {}) or {}
    google_snapshot = _snapshot(google, old_files, "google", synced_folders)
    nextcloud_snapshot = _snapshot(nextcloud, old_files, "nextcloud", synced_folders)
    copied_gn = 0
    copied_ng = 0
    conflicts = 0

    for relative in sorted(set(google_snapshot) | set(nextcloud_snapshot)):
        g = google_snapshot.get(relative)
        n = nextcloud_snapshot.get(relative)
        old = old_files.get(relative, {}) or {}
        if g is None and n is not None:
            _copy(nextcloud / relative, google / relative)
            copied_ng += 1
            continue
        if n is None and g is not None:
            _copy(google / relative, nextcloud / relative)
            copied_gn += 1
            continue
        if g is None or n is None or g["hash"] == n["hash"]:
            continue

        google_changed = old.get("google_hash") != g["hash"]
        nextcloud_changed = old.get("nextcloud_hash") != n["hash"]
        if google_changed and not nextcloud_changed:
            _copy(google / relative, nextcloud / relative)
            copied_gn += 1
        elif nextcloud_changed and not google_changed:
            _copy(nextcloud / relative, google / relative)
            copied_ng += 1
        else:
            _resolve_conflict(google, nextcloud, relative, g, n)
            conflicts += 1

    final_google = _snapshot(google, old_files, "google", synced_folders)
    final_nextcloud = _snapshot(nextcloud, old_files, "nextcloud", synced_folders)
    files = {
        relative: {
            "google_hash": final_google.get(relative, {}).get("hash"),
            "nextcloud_hash": final_nextcloud.get(relative, {}).get("hash"),
            "google_size": final_google.get(relative, {}).get("size"),
            "nextcloud_size": final_nextcloud.get(relative, {}).get("size"),
            "google_mtime_ns": final_google.get(relative, {}).get("mtime_ns"),
            "nextcloud_mtime_ns": final_nextcloud.get(relative, {}).get("mtime_ns"),
        }
        for relative in sorted(set(final_google) | set(final_nextcloud))
    }
    result = {
        "status": "SYNCED",
        "google_folder": str(google),
        "nextcloud_folder": str(nextcloud),
        "last_sync_at": time.time(),
        "copied_google_to_nextcloud": copied_gn,
        "copied_nextcloud_to_google": copied_ng,
        "conflicts": conflicts,
        "message": (
            f"Synchronizacja zakończona: Google→Nextcloud {copied_gn}, "
            f"Nextcloud→Google {copied_ng}, wybrano nowszą wersję {conflicts} razy."
        ),
        "files": files,
    }
    _save(path, result)
    return result


def run_forever(config, interval: float | None = None) -> None:  # pragma: no cover
    delay = float(interval or config.get("cloud_sync.mirror_interval_seconds", 60))
    while True:
        try:
            result = sync_once(config)
            print(f"[cloud-sync] {result['message']}")
        except Exception as exc:
            print(f"[cloud-sync] error: {exc}")
        time.sleep(max(delay, 10))


def read_status(config) -> dict:
    return _load(config.work_folder / "cloud_mirror_state.json")


def _snapshot(
    root: Path,
    previous: dict | None = None,
    side: str = "",
    synced_folders: set[str] | None = None,
) -> dict[str, dict]:
    result = {}
    previous = previous or {}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or _ignored(path.name):
            continue
        # Only product folders under Gotowe do sklepu and Opublikowane are
        # mirrored. Loose files and unrelated folders in FolderSync stay out.
        relative_path = path.relative_to(root)
        if len(relative_path.parts) < 3:
            continue
        if synced_folders and relative_path.parts[0] not in synced_folders:
            continue
        try:
            stat = path.stat()
            relative = str(relative_path).replace("\\", "/")
            cached = previous.get(relative, {}) or {}
            cached_hash = cached.get(f"{side}_hash") if side else None
            unchanged = (
                cached_hash
                and cached.get(f"{side}_size") == stat.st_size
                and cached.get(f"{side}_mtime_ns") == stat.st_mtime_ns
            )
            result[relative] = {
                "hash": cached_hash if unchanged else _sha256(path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "mtime_ns": stat.st_mtime_ns,
            }
        except OSError:
            continue
    return result


def _resolve_conflict(
    google_root: Path,
    nextcloud_root: Path,
    relative: str,
    google_info: dict,
    nextcloud_info: dict,
) -> None:
    google_path, nextcloud_path = google_root / relative, nextcloud_root / relative
    if google_info["mtime"] >= nextcloud_info["mtime"]:
        _copy(google_path, nextcloud_path)
    else:
        _copy(nextcloud_path, google_path)


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".workshop3d-syncing-{target.name}.tmp")
    shutil.copy2(source, temp)
    os.replace(temp, target)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ignored(name: str) -> bool:
    lowered = name.casefold()
    return lowered.startswith(".workshop3d-syncing-") or lowered.endswith(_IGNORE_SUFFIXES)


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
