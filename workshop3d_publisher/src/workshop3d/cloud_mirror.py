"""Non-destructive mirror between Google and Nextcloud ``Folder Sync``.

Two directions are supported, selected by ``cloud_sync.mirror_direction``:

``google_to_nextcloud`` (default)
    One-way push. Google ``Folder Sync`` is the working area and the single
    source of truth; Nextcloud ``Folder Sync`` is the post-sale archive.
    Files only ever travel Google -> Nextcloud. A path that exists solely on
    Nextcloud is left alone: that is the archive holding a product already
    cleaned out of the working area, and pulling it back would refill the
    inbox with things that were deliberately published and put away.

``two_way``
    The older behaviour. New and changed files flow both ways and, when both
    sides changed the same relative path, the newer file wins.

In both directions deletions are never propagated, and no duplicate product or
conflict folders are created. The explicit completed-product move is handled
atomically by :mod:`cloud_sync` on both roots, outside this generic rule.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from . import cloud_sync
from .nextcloud_api import NextcloudError, NextcloudWebDAV

_IGNORE_SUFFIXES = (".tmp", ".part", ".crdownload")

DIRECTION_ONE_WAY = "google_to_nextcloud"
DIRECTION_TWO_WAY = "two_way"


def direction(config) -> str:
    """Configured mirror direction, defaulting to the one-way push."""
    value = str(config.get("cloud_sync.mirror_direction", DIRECTION_ONE_WAY) or "").strip()
    return DIRECTION_TWO_WAY if value == DIRECTION_TWO_WAY else DIRECTION_ONE_WAY


def _pushes_only(config) -> bool:
    return direction(config) == DIRECTION_ONE_WAY


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

    remote = None if nextcloud is not None else NextcloudWebDAV.from_config(config)
    if google is None or (nextcloud is None and remote is None):
        status = {
            "status": "WAITING",
            "google_folder": str(google) if google else None,
            "nextcloud_folder": str(nextcloud) if nextcloud else None,
            "last_sync_at": previous.get("last_sync_at"),
            "copied_google_to_nextcloud": 0,
            "copied_nextcloud_to_google": 0,
            "conflicts": 0,
            "message": (
                "Google jest połączony, ale Nextcloud wymaga jednorazowego "
                "potwierdzenia w przeglądarce."
                if google is not None
                else "Czekam na lokalny Google FolderSync."
            ),
            "files": previous.get("files", {}),
        }
        _save(path, status)
        return status

    if remote is not None:
        try:
            return _sync_remote_nextcloud(
                config,
                google,
                remote,
                previous,
                path,
                synced_folders,
            )
        except (NextcloudError, OSError) as exc:
            status = {
                "status": "WAITING",
                "google_folder": str(google),
                "nextcloud_folder": f"WebDAV: {remote.server}/Folder Sync",
                "last_sync_at": previous.get("last_sync_at"),
                "copied_google_to_nextcloud": 0,
                "copied_nextcloud_to_google": 0,
                "conflicts": 0,
                "message": f"Nextcloud chwilowo niedostępny: {exc}",
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
    one_way = _pushes_only(config)

    for relative in sorted(set(google_snapshot) | set(nextcloud_snapshot)):
        g = google_snapshot.get(relative)
        n = nextcloud_snapshot.get(relative)
        old = old_files.get(relative, {}) or {}
        if g is None and n is not None:
            # One-way: this is the archive keeping a product that already left
            # the working area. Restoring it would undo the cleanup.
            if one_way:
                continue
            _copy(nextcloud / relative, google / relative)
            copied_ng += 1
            continue
        if n is None and g is not None:
            _copy(google / relative, nextcloud / relative)
            copied_gn += 1
            continue
        if g is None or n is None or g["hash"] == n["hash"]:
            continue

        if one_way:
            # Google is the source of truth: its version always wins.
            _copy(google / relative, nextcloud / relative)
            copied_gn += 1
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
        "direction": direction(config),
        "message": (
            f"Wysłano do magazynu: Google→Nextcloud {copied_gn} plików."
            if one_way
            else (
                f"Synchronizacja zakończona: Google→Nextcloud {copied_gn}, "
                f"Nextcloud→Google {copied_ng}, wybrano nowszą wersję {conflicts} razy."
            )
        ),
        "files": files,
    }
    _save(path, result)
    return result


def _sync_remote_nextcloud(
    config,
    google: Path,
    remote: NextcloudWebDAV,
    previous: dict,
    state_path: Path,
    synced_folders: set[str],
) -> dict:
    """Mirror a mounted Google folder directly to Nextcloud WebDAV."""
    old_files = previous.get("files", {}) or {}
    google_snapshot = _snapshot(google, old_files, "google", synced_folders)
    nextcloud_snapshot = remote.snapshot(synced_folders)
    copied_gn = 0
    copied_ng = 0
    conflicts = 0
    one_way = _pushes_only(config)

    for relative in sorted(set(google_snapshot) | set(nextcloud_snapshot)):
        g = google_snapshot.get(relative)
        n = nextcloud_snapshot.get(relative)
        old = old_files.get(relative, {}) or {}
        if g is None and n is not None:
            # One-way: the archive keeps what already left the working area.
            if one_way:
                continue
            remote.download(relative, google / relative)
            copied_ng += 1
            continue
        if n is None and g is not None:
            remote.upload(google / relative, relative)
            copied_gn += 1
            continue
        if g is None or n is None:
            continue

        google_changed = old.get("google_hash") != g["hash"]
        nextcloud_changed = old.get("nextcloud_hash") != n["hash"]
        if not google_changed and not nextcloud_changed:
            continue

        # On the first direct-WebDAV pass, compare same-sized files once.  A
        # Nextcloud ETag is not the same algorithm as our local SHA-256.
        if not old and g["size"] == n["size"]:
            if _sha256_bytes(remote.download_bytes(relative)) == g["hash"]:
                continue

        if one_way:
            # Nothing is pulled down; a Nextcloud-side edit is simply overwritten
            # by the working copy on the next pass.
            remote.upload(google / relative, relative)
            copied_gn += 1
            continue

        if google_changed and not nextcloud_changed:
            remote.upload(google / relative, relative)
            copied_gn += 1
        elif nextcloud_changed and not google_changed:
            remote.download(relative, google / relative)
            copied_ng += 1
        else:
            if g["mtime"] >= n["mtime"]:
                remote.upload(google / relative, relative)
                copied_gn += 1
            else:
                remote.download(relative, google / relative)
                copied_ng += 1
            conflicts += 1

    final_google = _snapshot(google, {}, "google", synced_folders)
    final_nextcloud = remote.snapshot(synced_folders)
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
        "nextcloud_folder": f"WebDAV: {remote.server}/Folder Sync",
        "last_sync_at": time.time(),
        "copied_google_to_nextcloud": copied_gn,
        "copied_nextcloud_to_google": copied_ng,
        "conflicts": conflicts,
        "direction": direction(config),
        "message": (
            f"Wysłano do magazynu na Nextcloud: {copied_gn} plików."
            if one_way
            else (
                f"Chmury połączone bezpośrednio: Google→Nextcloud {copied_gn}, "
                f"Nextcloud→Google {copied_ng}, wybrano nowszą wersję {conflicts} razy."
            )
        ),
        "files": files,
    }
    _save(state_path, result)
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
