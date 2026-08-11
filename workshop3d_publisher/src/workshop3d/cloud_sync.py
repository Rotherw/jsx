"""Synchronise the same finished product folder with both clouds.

The normal transport is Google Drive for desktop plus Nextcloud Desktop.  Both
clients expose ordinary Windows folders, so the publisher can work without
copying browser cookies or passwords.  Optional Google Drive API / Nextcloud
WebDAV fallbacks are kept for installations that already have credentials.

The cloud layout is deliberately simple and identical on both sides::

    FolderSync/Gotowe do sklepu/<folder produktu>/...
    Folder Sync/Gotowe do sklepu/<folder produktu>/...

After the full run the product folder is moved on both sides to the sibling
``Opublikowane`` directory.

No extra product-id folder and no sync manifest are created.
"""
from __future__ import annotations

import base64
import configparser
import fnmatch
import hashlib
import os
import re
import shutil
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .asset_hosts import AssetHostError, get_asset_host

PROVIDERS = ("google_drive", "nextcloud")
PROVIDER_SUCCESS = {"COPIED_LOCAL", "UPLOADED"}
ARCHIVE_SUCCESS = {"MOVED", "ALREADY_MOVED"}
_TEMP_SUFFIXES = (".tmp", ".part", ".crdownload")
SYNC_LOCK = threading.RLock()

# Source file plus its path relative to the finished product folder.
Artifact = tuple[Path, Path]


def enabled(config) -> bool:
    return bool(config.get("cloud_sync.enabled", False))


def succeeded(result: dict | None) -> bool:
    return bool(result and result.get("status") == "SYNCED")


def pending(result: dict | None) -> bool:
    return bool(result and result.get("status") == "WAITING")


def should_retry(result: dict | None, now: float | None = None) -> bool:
    if not pending(result):
        return False
    retry_at = result.get("next_retry_at")
    return retry_at is not None and float(retry_at) <= (now or time.time())


def inbox_name(config) -> str:
    """Name of the single drop subfolder inside both Folder Sync roots."""
    raw = str(config.get("cloud_sync.inbox_folder", "Gotowe do sklepu") or "")
    return _safe_name(Path(raw.replace("\\", "/")).name or "Gotowe do sklepu")


def published_name(config) -> str:
    raw = str(config.get("cloud_sync.published_folder", "Opublikowane") or "")
    return _safe_name(Path(raw.replace("\\", "/")).name or "Opublikowane")


def archived(result: dict | None) -> bool:
    return bool(result and result.get("status") == "ARCHIVED")


def sync_product(record, config, workspace: str | Path | None = None) -> dict:
    """Make the original finished folder available under both cloud inboxes.

    ``workspace`` is accepted for compatibility with older callers, but the
    source is intentionally ``record.folder_path``.  This keeps the exact
    folder the user supplied instead of creating a second ZIP/PNG-only folder.
    """
    with SYNC_LOCK:
        return _sync_product_unlocked(record, config, workspace)


def _sync_product_unlocked(record, config, workspace: str | Path | None = None) -> dict:
    del workspace
    previous = record.cloud_sync or {}
    paths = _source_files(Path(record.folder_path), config)
    if not paths:
        return _aggregate(
            {
                provider: _failure(
                    config,
                    _attempt(previous, provider),
                    "Gotowy folder produktu nie zawiera plików.",
                )
                for provider in PROVIDERS
            }
        )

    targets = {
        "google_drive": _sync_google(
            record, config, paths, _attempt(previous, "google_drive")
        ),
        "nextcloud": _sync_nextcloud(
            record, config, paths, _attempt(previous, "nextcloud")
        ),
    }
    return _aggregate(targets)


def archive_product(record, config) -> dict:
    """Move a completed product from ``Gotowe`` to sibling ``Opublikowane``.

    This is the one deliberate deletion from the inbox: both cloud roots are
    moved during the same locked operation, so the background mirror cannot
    restore the old queue entry in between.
    """
    with SYNC_LOCK:
        previous = record.cloud_archive or {}
        targets = {
            "google_drive": _archive_provider(
                record,
                config,
                "google_drive",
                discover_google_folder,
                _attempt(previous, "google_drive"),
            ),
            "nextcloud": _archive_provider(
                record,
                config,
                "nextcloud",
                discover_nextcloud_folder,
                _attempt(previous, "nextcloud"),
            ),
        }
        all_done = all(
            targets.get(name, {}).get("status") in ARCHIVE_SUCCESS
            for name in PROVIDERS
        )
        retry_times = [
            float(item["next_retry_at"])
            for item in targets.values()
            if item.get("next_retry_at") is not None
        ]
        return {
            "status": "ARCHIVED" if all_done else "WAITING",
            "targets": targets,
            "archived_at": time.time() if all_done else None,
            "next_retry_at": min(retry_times) if retry_times else None,
            "message": (
                "Folder przeniesiono w obu chmurach do Opublikowane."
                if all_done
                else "Czekam, aby przenieść folder w obu chmurach do Opublikowane."
            ),
        }


def _archive_provider(
    record,
    config,
    provider: str,
    discover,
    attempts: int,
) -> dict:
    label = "Google FolderSync" if provider == "google_drive" else "Nextcloud Folder Sync"
    try:
        root = discover(config)
    except OSError as exc:
        return _failure(config, attempts, f"{label}: {exc}")
    if root is None:
        return _failure(config, attempts, f"Czekam na lokalny {label}.")

    source = root / inbox_name(config) / _safe_name(record.folder_name)
    destination = root / published_name(config) / _safe_name(record.folder_name)
    try:
        moved = _move_product_folder(source, destination)
    except OSError as exc:
        return _failure(config, attempts, f"{label}: {exc}")

    if provider == "google_drive" and destination.is_dir():
        # The persistent record follows the canonical cloud copy after
        # completion, regardless of whether this run started in Google or in
        # the optional local fallback inbox.
        record.folder_path = str(destination)
    return {
        "status": "MOVED" if moved else "ALREADY_MOVED",
        "attempts": attempts,
        "destination": str(destination),
        "archived_at": time.time(),
        "next_retry_at": None,
        "message": f"Folder jest w {label}/{published_name(config)}.",
    }


def _move_product_folder(source: Path, destination: Path) -> bool:
    if not source.exists():
        if destination.is_dir():
            return False
        raise OSError(f"nie znaleziono folderu produktu: {source}")
    if not source.is_dir() or source.is_symlink():
        raise OSError(f"nieprawidłowy folder produktu: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        try:
            os.replace(source, destination)
        except OSError:
            shutil.move(str(source), str(destination))
        return True
    if not destination.is_dir():
        raise OSError(f"miejsce docelowe nie jest folderem: {destination}")

    # Merge into an already existing folder of the same name without creating
    # a numbered duplicate. Source files are authoritative for this completed
    # run; unrelated files already in Opublikowane remain untouched.
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and _fingerprint(path) == _fingerprint(target):
            path.unlink()
        else:
            os.replace(path, target)
    for directory in sorted(
        (path for path in source.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    source.rmdir()
    return True


def discover_google_folder(config) -> Path | None:
    """Find the local desktop-client root that represents Google FolderSync."""
    explicit = str(config.get("cloud_sync.google_drive.local_folder", "") or "").strip()
    folder_name = str(
        config.get("cloud_sync.google_drive.folder_name", "FolderSync") or "FolderSync"
    )
    return _discover_folder(
        explicit,
        folder_name,
        env_names=("GOOGLE_DRIVE_FOLDER", "GOOGLE_DRIVE_PATH"),
        bases=_google_bases(),
    )


def discover_nextcloud_folder(config) -> Path | None:
    """Find the local desktop-client root that represents Nextcloud Folder Sync."""
    explicit = str(config.get("cloud_sync.nextcloud.local_folder", "") or "").strip()
    folder_name = str(
        config.get("cloud_sync.nextcloud.folder_path", "Folder Sync") or "Folder Sync"
    )
    leaf = Path(folder_name.replace("\\", "/")).name or "Folder Sync"
    bases = _nextcloud_bases()
    bases.extend(_nextcloud_config_bases())
    return _discover_folder(
        explicit,
        leaf,
        env_names=("NEXTCLOUD_FOLDER", "NEXTCLOUD_PATH"),
        bases=bases,
    )


def discover_google_inbox(config, *, create: bool = True) -> Path | None:
    return _inbox(discover_google_folder(config), inbox_name(config), create=create)


def discover_nextcloud_inbox(config, *, create: bool = True) -> Path | None:
    return _inbox(discover_nextcloud_folder(config), inbox_name(config), create=create)


def _inbox(root: Path | None, name: str, *, create: bool) -> Path | None:
    if root is None:
        return None
    path = root / name
    if create:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
    return path if path.is_dir() else None


def _sync_google(record, config, paths: list[Artifact], attempts: int) -> dict:
    try:
        local = discover_google_inbox(config)
    except OSError as exc:
        local = None
        local_error = str(exc)
    else:
        local_error = ""
    if local is not None:
        try:
            destination = _copy_product(record, paths, local)
        except OSError as exc:
            return _failure(config, attempts, f"Google FolderSync: {exc}")
        return _success(
            attempts,
            "COPIED_LOCAL",
            str(destination),
            paths,
            "Gotowy folder jest w Google FolderSync/Gotowe do sklepu.",
        )

    settings = config.get("asset_hosts.google_drive", {}) or {}
    env_name = str(settings.get("credentials_env", "GOOGLE_APPLICATION_CREDENTIALS"))
    credential_path = os.environ.get(env_name, "")
    if credential_path and Path(credential_path).is_file():
        host = get_asset_host(
            "google_drive",
            config,
            {
                "root_folder_id": config.get("cloud_sync.google_drive.folder_id", ""),
                "root_folder_name": config.get(
                    "cloud_sync.google_drive.folder_name", "FolderSync"
                ),
                "parent_folder_names": [inbox_name(config)],
                "product_folder_name": _safe_name(record.folder_name),
                "relative_paths": {
                    str(source): relative.as_posix() for source, relative in paths
                },
                "make_public": False,
                "update_existing": True,
            },
        )
        try:
            if host is None:
                raise AssetHostError("Brak modułu Google Drive.")
            # The desktop-client path is preferred because it preserves nested
            # paths.  API fallback still uploads every file idempotently.
            host.host(record.product_id, [source for source, _ in paths])
        except Exception as exc:
            return _failure(config, attempts, f"Google Drive API: {exc}")
        return _success(
            attempts,
            "UPLOADED",
            f"Google Drive/FolderSync/{inbox_name(config)}/{record.folder_name}",
            paths,
            "Gotowy folder został prywatnie wgrany do wskazanego Google Drive.",
        )

    detail = f" ({local_error})" if local_error else ""
    return _failure(
        config,
        attempts,
        f"Czekam na lokalny Google Drive/FolderSync/{inbox_name(config)}{detail}",
    )


def _sync_nextcloud(record, config, paths: list[Artifact], attempts: int) -> dict:
    try:
        local = discover_nextcloud_inbox(config)
    except OSError as exc:
        local = None
        local_error = str(exc)
    else:
        local_error = ""
    if local is not None:
        try:
            destination = _copy_product(record, paths, local)
        except OSError as exc:
            return _failure(config, attempts, f"Nextcloud Folder Sync: {exc}")
        return _success(
            attempts,
            "COPIED_LOCAL",
            str(destination),
            paths,
            "Ten sam gotowy folder jest w Nextcloud Folder Sync.",
        )

    username_env = str(
        config.get("cloud_sync.nextcloud.username_env", "NEXTCLOUD_USERNAME")
    )
    password_env = str(
        config.get("cloud_sync.nextcloud.password_env", "NEXTCLOUD_APP_PASSWORD")
    )
    username, password = os.environ.get(username_env), os.environ.get(password_env)
    if username and password:
        try:
            destination = _upload_nextcloud_webdav(
                record, config, paths, username, password
            )
        except (HTTPError, URLError, OSError) as exc:
            return _failure(config, attempts, f"Nextcloud WebDAV: {exc}")
        return _success(
            attempts,
            "UPLOADED",
            destination,
            paths,
            "Ten sam gotowy folder został wgrany do Nextcloud Folder Sync.",
        )

    detail = f" ({local_error})" if local_error else ""
    return _failure(
        config,
        attempts,
        f"Czekam na lokalny Nextcloud/Folder Sync/{inbox_name(config)}{detail}",
    )


def _copy_product(record, paths: list[Artifact], inbox: Path) -> Path:
    destination = inbox / _safe_name(record.folder_name)
    destination.mkdir(parents=True, exist_ok=True)
    for source, relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            same_file = source.resolve() == target.resolve()
        except OSError:
            same_file = False
        if same_file:
            continue
        if target.is_file() and _fingerprint(source) == _fingerprint(target):
            continue
        temp = target.with_name(f".workshop3d-syncing-{target.name}.tmp")
        shutil.copy2(source, temp)
        os.replace(temp, target)
    return destination


def _upload_nextcloud_webdav(
    record,
    config,
    paths: list[Artifact],
    username: str,
    password: str,
) -> str:
    server = str(
        config.get("cloud_sync.nextcloud.server_url", "https://cloud.workshop3d.pl")
    ).rstrip("/")
    configured_root = str(
        config.get("cloud_sync.nextcloud.folder_path", "Folder Sync")
    ).strip("/ ")
    root_parts = [part for part in configured_root.replace("\\", "/").split("/") if part]
    product_parts = root_parts + [inbox_name(config), _safe_name(record.folder_name)]
    dav_root = f"{server}/remote.php/dav/files/{quote(username, safe='')}"
    auth = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()

    product_url = _mkcol_chain(dav_root, product_parts, auth)
    created_dirs: set[tuple[str, ...]] = set()
    for source, relative in paths:
        parent_parts = tuple(relative.parts[:-1])
        if parent_parts and parent_parts not in created_dirs:
            _mkcol_chain(product_url, list(parent_parts), auth)
            created_dirs.add(parent_parts)
        encoded_relative = "/".join(quote(part, safe="") for part in relative.parts)
        _request(f"{product_url}/{encoded_relative}", "PUT", auth, source.read_bytes())

    display_path = "/".join(product_parts)
    return f"{server}/index.php/apps/files/files?dir=/{quote(display_path, safe='/')}"


def _mkcol_chain(base: str, parts: list[str], auth: str) -> str:
    current = base.rstrip("/")
    for part in parts:
        current += "/" + quote(part, safe="")
        try:
            _request(current, "MKCOL", auth)
        except HTTPError as exc:
            if exc.code != 405:  # 405 = collection already exists
                raise
    return current


def _request(url: str, method: str, auth: str, data: bytes | None = None) -> bytes:
    request = Request(url, data=data, method=method, headers={"Authorization": auth})
    with urlopen(request, timeout=120) as response:
        return response.read()


def _discover_folder(
    explicit: str,
    folder_name: str,
    *,
    env_names: tuple[str, ...],
    bases: list[Path],
) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    candidates: list[Path] = []
    for env_name in env_names:
        raw = os.environ.get(env_name)
        if raw:
            base = Path(raw)
            candidates.append(
                base if base.name.casefold() == folder_name.casefold() else base / folder_name
            )
    for base in bases:
        if base.is_dir():
            candidates.append(
                base if base.name.casefold() == folder_name.casefold() else base / folder_name
            )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
        if candidate.parent.is_dir():
            try:
                candidate.mkdir(exist_ok=True)
                return candidate
            except OSError:
                continue
    return None


def _google_bases() -> list[Path]:
    profile = Path(os.environ.get("USERPROFILE") or Path.home())
    bases = [
        profile / "My Drive",
        profile / "Mój dysk",
        profile / "Google Drive" / "My Drive",
        profile / "Google Drive" / "Mój dysk",
        profile / "Google Drive",
    ]
    if os.name == "nt":
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            bases.extend(
                [
                    Path(f"{letter}:/My Drive"),
                    Path(f"{letter}:/Mój dysk"),
                    Path(f"{letter}:/Google Drive/My Drive"),
                    Path(f"{letter}:/Google Drive/Mój dysk"),
                ]
            )
    return bases


def _nextcloud_bases() -> list[Path]:
    profile = Path(os.environ.get("USERPROFILE") or Path.home())
    return [profile / "Nextcloud", profile / "Chmura", profile / "WorkShop3D Cloud"]


def _nextcloud_config_bases() -> list[Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    config_path = Path(appdata) / "Nextcloud" / "nextcloud.cfg"
    if not config_path.is_file():
        return []
    parser = configparser.ConfigParser(strict=False)
    try:
        parser.read(config_path, encoding="utf-8")
    except (OSError, configparser.Error):
        return []
    bases: list[Path] = []
    for section in parser.sections():
        for key, value in parser.items(section):
            if "localpath" in key.casefold() and value.strip():
                bases.append(Path(value.strip()))
    return bases


def _source_files(folder: Path, config) -> list[Artifact]:
    if not folder.is_dir():
        return []
    patterns = config.get("trigger.ignore_patterns", []) or []
    result: list[Artifact] = []
    for source in sorted(folder.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        lowered = source.name.casefold()
        if lowered.startswith(".workshop3d-syncing-") or lowered.endswith(_TEMP_SUFFIXES):
            continue
        if any(fnmatch.fnmatch(source.name, pattern) for pattern in patterns):
            continue
        result.append((source, source.relative_to(folder)))
    return result


def _safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", value).strip(" .") or "product"


def _fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return path.stat().st_size, digest.hexdigest()


def _attempt(previous: dict, provider: str) -> int:
    return int((previous.get("targets", {}).get(provider, {}) or {}).get("attempts", 0)) + 1


def _success(
    attempts: int,
    status: str,
    destination: str,
    paths: list[Artifact],
    message: str,
) -> dict:
    return {
        "status": status,
        "attempts": attempts,
        "destination": destination,
        "files": [relative.as_posix() for _, relative in paths],
        "synced_at": time.time(),
        "next_retry_at": None,
        "message": message,
    }


def _failure(config, attempts: int, message: str) -> dict:
    delays = config.get("cloud_sync.retry_seconds", [60, 300, 900, 3600]) or [3600]
    try:
        delay = max(1, int(delays[min(attempts - 1, len(delays) - 1)]))
    except (TypeError, ValueError, IndexError):
        delay = 3600
    return {
        "status": "WAITING",
        "attempts": attempts,
        "synced_at": None,
        "next_retry_at": time.time() + delay,
        "message": message,
    }


def _aggregate(targets: dict[str, dict]) -> dict:
    all_done = all(
        targets.get(name, {}).get("status") in PROVIDER_SUCCESS for name in PROVIDERS
    )
    retry_times = [
        float(item["next_retry_at"])
        for item in targets.values()
        if item.get("next_retry_at") is not None
    ]
    return {
        "status": "SYNCED" if all_done else "WAITING",
        "targets": targets,
        "synced_at": time.time() if all_done else None,
        "next_retry_at": min(retry_times) if retry_times else None,
        "message": (
            "Ten sam gotowy folder jest w Google FolderSync i Nextcloud Folder Sync."
            if all_done
            else "Czekam na oba foldery chmurowe; ponowię automatycznie."
        ),
    }
