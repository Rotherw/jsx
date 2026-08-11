"""Official Nextcloud Login Flow v2 and direct WebDAV access.

The account password and browser cookies are never copied.  Nextcloud creates
a dedicated, revocable app password which is kept only in the publisher's
git-ignored local secrets file.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .config import DEFAULT_CONFIG
from . import secrets_env
from .browser_open import open_in_chrome

USER_AGENT = "WorkShop3D-Publisher/0.4"
DAV = "{DAV:}"


@dataclass(frozen=True)
class NextcloudCredentials:
    server: str
    username: str
    app_password: str


@dataclass(frozen=True)
class _Response:
    status_code: int
    content: bytes
    headers: object

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> dict:
        value = json.loads(self.content.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")
        return value


class NextcloudError(RuntimeError):
    """A clear, user-facing Nextcloud connection or WebDAV failure."""


def get_credentials(config) -> NextcloudCredentials | None:
    server = str(
        config.get("cloud_sync.nextcloud.server_url", "https://cloud.workshop3d.pl")
    ).rstrip("/")
    username_env = str(
        config.get("cloud_sync.nextcloud.username_env", "NEXTCLOUD_USERNAME")
    )
    password_env = str(
        config.get("cloud_sync.nextcloud.password_env", "NEXTCLOUD_APP_PASSWORD")
    )
    username = os.environ.get(username_env, "").strip()
    password = os.environ.get(password_env, "").strip()
    return (
        NextcloudCredentials(server, username, password)
        if username and password
        else None
    )


def store_credentials(config, credentials: NextcloudCredentials) -> None:
    """Store only Nextcloud's revocable app password, never the main password."""
    config.set("cloud_sync.nextcloud.server_url", credentials.server.rstrip("/"))
    config.set("cloud_sync.nextcloud.login_name", credentials.username)
    config.save()
    secrets_env.save_secrets(
        DEFAULT_CONFIG.parent / ".env",
        {
            "NEXTCLOUD_USERNAME": credentials.username,
            "NEXTCLOUD_APP_PASSWORD": credentials.app_password,
        },
    )


def connect_login_flow(
    config,
    *,
    timeout: float = 20 * 60,
    poll_interval: float = 2.0,
    open_browser=None,
    opener=urlopen,
) -> NextcloudCredentials:
    """Authorize in the default browser using Nextcloud Login Flow v2."""
    server = str(
        config.get("cloud_sync.nextcloud.server_url", "https://cloud.workshop3d.pl")
    ).rstrip("/")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    start = _http(
        opener,
        Request(f"{server}/index.php/login/v2", data=b"", method="POST", headers=headers),
        timeout=30,
    )
    if start.status_code not in (200, 201):
        raise NextcloudError(f"Nie udało się rozpocząć logowania (HTTP {start.status_code}).")
    try:
        data = start.json()
        login_url = str(data["login"])
        poll_url = str(data["poll"]["endpoint"])
        token = str(data["poll"]["token"])
    except (KeyError, TypeError, ValueError) as exc:
        raise NextcloudError(f"Nextcloud zwrócił nieprawidłowe logowanie: {exc}") from exc

    _write_status(config, "AUTHORIZING", "Potwierdź połączenie w otwartej stronie Nextcloud.")
    browser = open_browser or open_in_chrome
    if not browser(login_url):
        raise NextcloudError(f"Otwórz w przeglądarce: {login_url}")

    deadline = time.monotonic() + max(timeout, 1)
    while time.monotonic() < deadline:
        response = _http(
            opener,
            Request(
                poll_url,
                data=urlencode({"token": token}).encode("ascii"),
                method="POST",
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            ),
            timeout=30,
        )
        if response.status_code == 404:
            time.sleep(max(poll_interval, 0.1))
            continue
        if response.status_code != 200:
            raise NextcloudError(f"Błąd logowania Nextcloud (HTTP {response.status_code}).")
        try:
            result = response.json()
            credentials = NextcloudCredentials(
                str(result["server"]).rstrip("/"),
                str(result["loginName"]),
                str(result["appPassword"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NextcloudError(f"Nextcloud zwrócił nieprawidłową odpowiedź: {exc}") from exc
        store_credentials(config, credentials)
        _write_status(config, "CONNECTED", "Nextcloud połączony. Synchronizacja działa w tle.")
        return credentials

    _write_status(config, "WAITING", "Nie potwierdzono połączenia Nextcloud.")
    raise NextcloudError("Minął czas na potwierdzenie połączenia Nextcloud.")


def connection_status(config) -> dict:
    path = config.work_folder / "nextcloud_connection.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _write_status(config, status: str, message: str) -> None:
    path = config.work_folder / "nextcloud_connection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(
            {"status": status, "message": message, "updated_at": time.time()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(temp, path)


def _http(opener, request: Request, *, timeout: float) -> _Response:
    try:
        with opener(request, timeout=timeout) as response:
            return _Response(
                int(response.getcode()),
                response.read(),
                getattr(response, "headers", {}),
            )
    except HTTPError as exc:
        return _Response(exc.code, exc.read(), exc.headers)
    except (URLError, OSError) as exc:
        raise NextcloudError(f"Brak połączenia z Nextcloud: {exc}") from exc


class NextcloudWebDAV:
    """Small WebDAV client rooted at the configured ``Folder Sync``."""

    def __init__(
        self,
        credentials: NextcloudCredentials,
        root_folder: str = "Folder Sync",
        *,
        opener=urlopen,
    ):
        self.credentials = credentials
        self.server = credentials.server.rstrip("/")
        self.username = credentials.username
        self.root_parts = tuple(
            part for part in root_folder.replace("\\", "/").split("/") if part
        ) or ("Folder Sync",)
        self.opener = opener
        self.dav_root = (
            f"{self.server}/remote.php/dav/files/{quote(credentials.username, safe='')}"
        )
        token = base64.b64encode(
            f"{credentials.username}:{credentials.app_password}".encode("utf-8")
        ).decode("ascii")
        self.headers = {"User-Agent": USER_AGENT, "Authorization": f"Basic {token}"}

    @classmethod
    def from_config(cls, config) -> "NextcloudWebDAV | None":
        credentials = get_credentials(config)
        if credentials is None:
            return None
        root = str(config.get("cloud_sync.nextcloud.folder_path", "Folder Sync"))
        return cls(credentials, root)

    def validate(self) -> bool:
        response = self._request("PROPFIND", "", headers={"Depth": "0"})
        return response.status_code in (200, 207)

    def ensure_folder(self, relative: str | PurePosixPath = "") -> None:
        parts = self.root_parts + self._parts(relative)
        current: list[str] = []
        for part in parts:
            current.append(part)
            response = self._request("MKCOL", PurePosixPath(*current), root=False)
            if response.status_code not in (201, 405):
                self._raise(response, f"Nie można utworzyć folderu {'/'.join(current)}")

    def exists(self, relative: str | PurePosixPath) -> bool:
        response = self._request("PROPFIND", relative, headers={"Depth": "0"})
        if response.status_code == 404:
            return False
        if response.status_code not in (200, 207):
            self._raise(response, f"Nie można sprawdzić {relative}")
        return True

    def upload(self, source: Path, relative: str | PurePosixPath) -> None:
        relative = PurePosixPath(str(relative).replace("\\", "/"))
        self.ensure_folder(relative.parent if str(relative.parent) != "." else "")
        response = self._request(
            "PUT",
            relative,
            data=source.read_bytes(),
            headers={"X-OC-MTime": str(int(source.stat().st_mtime))},
        )
        if response.status_code not in (200, 201, 204):
            self._raise(response, f"Nie można wysłać {relative}")

    def download(self, relative: str | PurePosixPath, target: Path) -> None:
        response = self._request("GET", relative)
        if response.status_code != 200:
            self._raise(response, f"Nie można pobrać {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(f".workshop3d-syncing-{target.name}.tmp")
        temp.write_bytes(response.content)
        os.replace(temp, target)

    def download_bytes(self, relative: str | PurePosixPath) -> bytes:
        response = self._request("GET", relative)
        if response.status_code != 200:
            self._raise(response, f"Nie można pobrać {relative}")
        return response.content

    def move(self, source: str | PurePosixPath, destination: str | PurePosixPath) -> bool:
        destination = PurePosixPath(str(destination).replace("\\", "/"))
        self.ensure_folder(destination.parent if str(destination.parent) != "." else "")
        response = self._request(
            "MOVE",
            source,
            headers={"Destination": self._url(destination), "Overwrite": "T"},
        )
        if response.status_code in (201, 204):
            return True
        if response.status_code == 404 and self.exists(destination):
            return False
        self._raise(response, f"Nie można przenieść {source}")
        return False

    def snapshot(self, synced_folders: set[str]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for folder in sorted(synced_folders):
            self.ensure_folder(folder)
            self._walk(PurePosixPath(folder), result)
        return result

    def _walk(self, relative: PurePosixPath, result: dict[str, dict]) -> None:
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop><d:displayname/>'
            '<d:getlastmodified/><d:getcontentlength/><d:getetag/>'
            '<d:resourcetype/></d:prop></d:propfind>'
        ).encode("utf-8")
        response = self._request(
            "PROPFIND",
            relative,
            data=body,
            headers={"Depth": "1", "Content-Type": "application/xml"},
        )
        if response.status_code not in (200, 207):
            self._raise(response, f"Nie można odczytać {relative}")
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            raise NextcloudError(f"Nieprawidłowa odpowiedź WebDAV: {exc}") from exc

        current_url_path = unquote(urlsplit(self._url(relative)).path).rstrip("/")
        for item in root.findall(f"{DAV}response"):
            href = item.findtext(f"{DAV}href", "")
            href_path = unquote(urlsplit(href).path).rstrip("/")
            if href_path == current_url_path:
                continue
            prop = item.find(f"{DAV}propstat/{DAV}prop")
            if prop is None:
                continue
            name = (prop.findtext(f"{DAV}displayname") or PurePosixPath(href_path).name).strip()
            if not name or name in (".", ".."):
                continue
            child = relative / name
            resource = prop.find(f"{DAV}resourcetype")
            is_dir = resource is not None and resource.find(f"{DAV}collection") is not None
            if is_dir:
                self._walk(child, result)
                continue
            if len(child.parts) < 3:
                continue
            modified = prop.findtext(f"{DAV}getlastmodified", "")
            try:
                mtime = parsedate_to_datetime(modified).timestamp() if modified else 0.0
            except (TypeError, ValueError, OverflowError):
                mtime = 0.0
            try:
                size = int(prop.findtext(f"{DAV}getcontentlength", "0") or 0)
            except ValueError:
                size = 0
            etag = (prop.findtext(f"{DAV}getetag", "") or "").strip('"')
            result[child.as_posix()] = {
                "hash": etag or f"{size}:{int(mtime)}",
                "size": size,
                "mtime": mtime,
                "mtime_ns": int(mtime * 1_000_000_000),
            }

    def _parts(self, relative: str | PurePosixPath) -> tuple[str, ...]:
        raw = str(relative).replace("\\", "/").strip("/")
        return tuple(part for part in raw.split("/") if part and part != ".")

    def _url(self, relative: str | PurePosixPath = "", *, root: bool = True) -> str:
        parts = (self.root_parts if root else ()) + self._parts(relative)
        suffix = "/".join(quote(part, safe="") for part in parts)
        return f"{self.dav_root}/{suffix}" if suffix else self.dav_root

    def _request(
        self,
        method: str,
        relative: str | PurePosixPath,
        *,
        root: bool = True,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> _Response:
        request = Request(
            self._url(relative, root=root),
            data=data,
            method=method,
            headers={**self.headers, **(headers or {})},
        )
        return _http(self.opener, request, timeout=120)

    @staticmethod
    def _raise(response: _Response, message: str) -> None:
        detail = response.text[:200].replace("\n", " ").strip()
        suffix = f": {detail}" if detail else ""
        raise NextcloudError(f"{message} (HTTP {response.status_code}){suffix}")
