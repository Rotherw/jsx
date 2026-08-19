"""Direct Nextcloud auth and WebDAV transport require no desktop mirror."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from workshop3d import __main__ as mainmod
from workshop3d import cloud_mirror, cloud_sync, nextcloud_api
from workshop3d.models import ProductRecord


class DummyConfig:
    def __init__(self, work_folder: Path):
        self.values = {
            "cloud_sync.nextcloud.server_url": "https://cloud.workshop3d.pl",
            "cloud_sync.nextcloud.folder_path": "Folder Sync",
        }
        self.work_folder = work_folder
        self.saved = False

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def save(self):
        self.saved = True


class RawResponse:
    def __init__(self, status: int, value=b""):
        self.status = status
        self.value = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def getcode(self):
        return self.status

    def read(self):
        return self.value


def test_login_flow_opens_browser_and_stores_revocable_app_password(
    tmp_path, monkeypatch
):
    config = DummyConfig(tmp_path / "work")
    replies = iter(
        [
            RawResponse(
                200,
                {
                    "login": "https://cloud.workshop3d.pl/login/flow/abc",
                    "poll": {
                        "endpoint": "https://cloud.workshop3d.pl/login/poll",
                        "token": "poll-token",
                    },
                },
            ),
            RawResponse(404),
            RawResponse(
                200,
                {
                    "server": "https://cloud.workshop3d.pl",
                    "loginName": "rafal",
                    "appPassword": "app-only-password",
                },
            ),
        ]
    )
    requests = []
    opened = []

    def opener(request, timeout):
        requests.append((request.full_url, request.get_method(), request.data, timeout))
        return next(replies)

    monkeypatch.setattr(
        nextcloud_api, "DEFAULT_CONFIG", tmp_path / "config" / "config.yaml"
    )
    monkeypatch.delenv("NEXTCLOUD_USERNAME", raising=False)
    monkeypatch.delenv("NEXTCLOUD_APP_PASSWORD", raising=False)

    credentials = nextcloud_api.connect_login_flow(
        config,
        opener=opener,
        open_browser=lambda url: opened.append(url) or True,
        poll_interval=0.001,
    )

    assert opened == ["https://cloud.workshop3d.pl/login/flow/abc"]
    assert credentials.username == "rafal"
    assert config.saved is True
    assert requests[0][1] == "POST"
    assert b"poll-token" in requests[-1][2]
    secret_file = tmp_path / "config" / ".env"
    text = secret_file.read_text(encoding="utf-8")
    assert "NEXTCLOUD_USERNAME=rafal" in text
    assert "NEXTCLOUD_APP_PASSWORD=app-only-password" in text


def test_webdav_upload_and_move_use_the_configured_cloud_folder(tmp_path):
    calls = []

    def opener(request, timeout):
        calls.append(request)
        status = 405 if request.get_method() == "MKCOL" else 201
        return RawResponse(status)

    client = nextcloud_api.NextcloudWebDAV(
        nextcloud_api.NextcloudCredentials(
            "https://cloud.workshop3d.pl", "rafal", "app-password"
        ),
        opener=opener,
    )
    source = tmp_path / "model.stl"
    source.write_bytes(b"solid model")

    client.upload(source, "Gotowe do sklepu/Test/model.stl")
    assert client.move(
        "Gotowe do sklepu/Test", "Opublikowane/Test"
    ) is True

    put = next(call for call in calls if call.get_method() == "PUT")
    move = next(call for call in calls if call.get_method() == "MOVE")
    assert "Folder%20Sync/Gotowe%20do%20sklepu/Test/model.stl" in put.full_url
    assert put.data == b"solid model"
    assert move.headers["Destination"].endswith("Folder%20Sync/Opublikowane/Test")
    assert move.headers["Authorization"].startswith("Basic ")


def test_default_webdav_upload_streams_large_files(tmp_path, monkeypatch):
    source = tmp_path / "large-model.3mf"
    source.write_bytes(b"model-data" * 1024)
    observed = {}

    class Response:
        status_code = 201
        content = b""
        headers = {}

    def put(url, *, data, headers, timeout):
        observed["url"] = url
        observed["is_stream"] = hasattr(data, "read") and not isinstance(data, bytes)
        observed["body"] = data.read()
        observed["headers"] = headers
        observed["timeout"] = timeout
        return Response()

    client = nextcloud_api.NextcloudWebDAV(
        nextcloud_api.NextcloudCredentials(
            "https://cloud.workshop3d.pl", "rafal", "app-password"
        )
    )
    monkeypatch.setattr(client, "ensure_folder", lambda _relative="": None)
    import requests

    monkeypatch.setattr(requests, "put", put)
    client.upload(source, "Gotowe do sklepu/Test/large-model.3mf")

    assert observed["is_stream"] is True
    assert observed["body"] == source.read_bytes()
    assert observed["headers"]["Content-Length"] == str(source.stat().st_size)
    assert observed["headers"]["Authorization"].startswith("Basic ")
    assert observed["timeout"] == (30, 3600)
    assert "Folder%20Sync/Gotowe%20do%20sklepu/Test/large-model.3mf" in observed["url"]


class FakeRemote:
    server = "https://cloud.workshop3d.pl"

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.mtimes: dict[str, float] = {}
        self.moves = []

    def snapshot(self, _folders):
        return {
            path: {
                "hash": hashlib.sha256(value).hexdigest(),
                "size": len(value),
                "mtime": self.mtimes[path],
                "mtime_ns": int(self.mtimes[path] * 1_000_000_000),
            }
            for path, value in self.files.items()
        }

    def upload(self, source, relative):
        key = str(relative).replace("\\", "/")
        self.files[key] = Path(source).read_bytes()
        self.mtimes[key] = Path(source).stat().st_mtime

    def download(self, relative, target):
        key = str(relative).replace("\\", "/")
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.files[key])

    def download_bytes(self, relative):
        return self.files[str(relative).replace("\\", "/")]

    def move(self, source, destination):
        self.moves.append((str(source), str(destination)))
        return True


def test_web_nextcloud_one_way_never_pulls_the_archive_back(
    config, tmp_path, monkeypatch
):
    """Domyslnie WebDAV jest magazynem: pliki leca tylko w gore."""
    google = tmp_path / "google"
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.local_folder", "")
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.published_folder", "Opublikowane")
    local = google / "Gotowe do sklepu" / "Google Product" / "model.stl"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"from google")
    remote = FakeRemote()
    monkeypatch.setattr(cloud_sync, "discover_nextcloud_folder", lambda _config: None)
    monkeypatch.setattr(
        cloud_mirror.NextcloudWebDAV, "from_config", lambda _config: remote
    )
    state = tmp_path / "mirror.json"

    first = cloud_mirror.sync_once(config, state)
    assert first["status"] == "SYNCED"
    assert remote.files["Gotowe do sklepu/Google Product/model.stl"] == b"from google"

    # Paczka juz sprzedana i sprzatnieta z obszaru roboczego nie wraca.
    remote_path = "Gotowe do sklepu/Sold Product/preview.png"
    remote.files[remote_path] = b"archived"
    remote.mtimes[remote_path] = time.time() + 10
    second = cloud_mirror.sync_once(config, state)

    assert not (google / "Gotowe do sklepu" / "Sold Product").exists()
    assert second["copied_nextcloud_to_google"] == 0
    assert remote.files[remote_path] == b"archived"


def test_google_and_web_nextcloud_flow_in_both_directions(
    config, tmp_path, monkeypatch
):
    google = tmp_path / "google"
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.local_folder", "")
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.published_folder", "Opublikowane")
    config.set("cloud_sync.mirror_direction", cloud_mirror.DIRECTION_TWO_WAY)
    local = google / "Gotowe do sklepu" / "Google Product" / "model.stl"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"from google")
    remote = FakeRemote()
    monkeypatch.setattr(cloud_sync, "discover_nextcloud_folder", lambda _config: None)
    monkeypatch.setattr(
        cloud_mirror.NextcloudWebDAV, "from_config", lambda _config: remote
    )
    state = tmp_path / "mirror.json"

    first = cloud_mirror.sync_once(config, state)
    assert first["status"] == "SYNCED"
    assert remote.files["Gotowe do sklepu/Google Product/model.stl"] == b"from google"

    remote_path = "Gotowe do sklepu/Nextcloud Product/preview.png"
    remote.files[remote_path] = b"from nextcloud"
    remote.mtimes[remote_path] = time.time() + 10
    second = cloud_mirror.sync_once(config, state)

    assert (
        google / "Gotowe do sklepu" / "Nextcloud Product" / "preview.png"
    ).read_bytes() == b"from nextcloud"
    assert second["copied_nextcloud_to_google"] == 1


def test_first_run_uploads_all_existing_google_product_folders(
    config, tmp_path, monkeypatch
):
    """An empty Nextcloud receives every product already present in Google."""
    google = tmp_path / "Google Folder Sync"
    names = [
        "Czempion Inkwizycji Imperialnej",
        "Knight of the Golden Lion Imperial Guardian",
        "Maji_Ziemi_Dedyk_KF2",
        "Maji_water",
        "MAJI_Żywioł_Ognia",
        "Maji_Winter",
        "Maji_Ziemi",
    ]
    for index, name in enumerate(names):
        folder = google / "Gotowe do sklepu" / name
        folder.mkdir(parents=True)
        (folder / f"{name}.stl").write_bytes(f"model-{index}".encode())
        (folder / f"{name}.png").write_bytes(f"preview-{index}".encode())

    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.prefer_webdav", True)
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.published_folder", "Opublikowane")
    remote = FakeRemote()
    monkeypatch.setattr(
        cloud_mirror.NextcloudWebDAV, "from_config", lambda _config: remote
    )

    result = cloud_mirror.sync_once(config, tmp_path / "first-mirror.json")

    assert result["status"] == "SYNCED"
    assert result["copied_google_to_nextcloud"] == len(names) * 2
    assert {
        path.split("/")[1]
        for path in remote.files
        if path.startswith("Gotowe do sklepu/")
    } == set(names)


def test_background_connector_authorizes_then_runs_initial_mirror(
    config, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        mainmod.nextcloud_api.NextcloudWebDAV,
        "from_config",
        lambda _config: None,
    )
    monkeypatch.setattr(
        mainmod.nextcloud_api,
        "connect_login_flow",
        lambda _config, timeout: calls.append(("connect", timeout)),
    )
    monkeypatch.setattr(
        mainmod.cloud_mirror,
        "sync_once",
        lambda _config: calls.append(("mirror", None))
        or {"status": "SYNCED", "message": "copied"},
    )

    assert mainmod._connect_nextcloud_and_sync_once(config) is True
    assert calls == [("connect", 3 * 60), ("mirror", None)]


def test_product_upload_and_archive_use_webdav_when_no_desktop_folder(
    product_folder, config, tmp_path, monkeypatch
):
    source = product_folder(name="Remote Product")
    record = ProductRecord("remote", source.name, str(source))
    remote = FakeRemote()
    monkeypatch.setattr(cloud_sync, "discover_nextcloud_inbox", lambda _config: None)
    monkeypatch.setattr(
        cloud_sync.NextcloudWebDAV, "from_config", lambda _config: remote
    )

    result = cloud_sync._sync_nextcloud(
        record, config, cloud_sync._source_files(source, config), 0
    )
    archived = cloud_sync._archive_nextcloud_webdav(record, config, 0)

    assert result["status"] == "UPLOADED"
    assert "Gotowe do sklepu/Remote Product/Remote Product.stl" in remote.files
    assert archived["status"] == "MOVED"
    assert remote.moves == [
        ("Gotowe do sklepu/Remote Product", "Opublikowane/Remote Product")
    ]
