"""GoogleDriveHost tests using a fake Drive service (no network, no google libs)."""
from pathlib import Path

from workshop3d.config import Config
from workshop3d.asset_hosts.google_drive import GoogleDriveHost


class _Exec:
    def __init__(self, result): self._r = result
    def execute(self): return self._r


class FakeFiles:
    def __init__(self, drive): self.drive = drive

    def list(self, q, spaces=None, fields=None):
        # Return an existing match only if we've "created" it before.
        for fid, meta in self.drive.store.items():
            name_match = f"name='{meta['name']}'" in q
            is_folder = meta.get("mimeType") == "application/vnd.google-apps.folder"
            wants_folder = "mimeType='application/vnd.google-apps.folder'" in q
            parent_ok = (f"'{meta.get('parent')}' in parents" in q) or ("in parents" not in q)
            if name_match and parent_ok and (is_folder == wants_folder):
                return _Exec({"files": [{"id": fid, "name": meta["name"]}]})
        return _Exec({"files": []})

    def create(self, body=None, fields=None, media_body=None):
        self.drive.seq += 1
        fid = f"id{self.drive.seq}"
        parent = (body.get("parents") or [None])[0]
        self.drive.store[fid] = {"name": body["name"],
                                 "mimeType": body.get("mimeType", "file"),
                                 "parent": parent}
        return _Exec({"id": fid})

    def update(self, fileId=None, media_body=None):
        self.drive.updated.append((fileId, media_body))
        return _Exec({"id": fileId})


class FakePermissions:
    def __init__(self, drive): self.drive = drive
    def create(self, fileId=None, body=None):
        self.drive.public.add(fileId)
        return _Exec({"id": "perm"})


class FakeDrive:
    def __init__(self):
        self.store = {}
        self.public = set()
        self.updated = []
        self.seq = 0
    def files(self): return FakeFiles(self)
    def permissions(self): return FakePermissions(self)


def _config():
    return Config({"asset_hosts": {"google_drive": {"root_folder_name": "FolderSync"}}})


def test_uploads_makes_public_and_builds_cults_url(tmp_path):
    f = tmp_path / "WorkShop3D_Door.zip"
    f.write_bytes(b"zip")
    drive = FakeDrive()
    host = GoogleDriveHost(_config(), {"root_folder_name": "FolderSync"}, service=drive, media_factory=lambda path: path)

    urls = host.host("prod123", [f])
    assert list(urls.keys()) == ["WorkShop3D_Door.zip"]
    url = urls["WorkShop3D_Door.zip"]
    # Cults-compatible: exposes the filename+extension and is a direct download.
    assert "filename=WorkShop3D_Door.zip" in url
    assert "export=download" in url
    # The uploaded file was made public.
    assert len(drive.public) == 1
    # FolderSync + per-product subfolder were created.
    names = {m["name"] for m in drive.store.values()}
    assert "FolderSync" in names and "prod123" in names


def test_idempotent_no_duplicate_upload(tmp_path):
    f = tmp_path / "cover.png"
    f.write_bytes(b"png")
    drive = FakeDrive()
    host = GoogleDriveHost(_config(), {"root_folder_name": "FolderSync"}, service=drive, media_factory=lambda path: path)

    host.host("prodX", [f])
    files_after_first = dict(drive.store)
    # Fresh host (cold cache) -> must reuse existing folders/file, not duplicate.
    host2 = GoogleDriveHost(_config(), {"root_folder_name": "FolderSync"}, service=drive, media_factory=lambda path: path)
    host2.host("prodX", [f])
    assert drive.store.keys() == files_after_first.keys()


def test_uc_template(tmp_path):
    f = tmp_path / "x.zip"
    f.write_bytes(b"z")
    host = GoogleDriveHost(_config(), {"url_template": "uc"}, service=FakeDrive(), media_factory=lambda path: path)
    url = host.host("p", [f])["x.zip"]
    assert url.startswith("https://drive.google.com/uc?export=download")
    assert "filename=x.zip" in url


def test_exact_root_and_friendly_nested_folder_are_used_privately(tmp_path):
    f = tmp_path / "model.stl"
    f.write_bytes(b"stl")
    drive = FakeDrive()
    host = GoogleDriveHost(
        _config(),
        {
            "root_folder_id": "exact-user-folder-id",
            "root_folder_name": "FolderSync",
            "parent_folder_names": ["Gotowe do sklepu"],
            "product_folder_name": "Friendly Product",
            "make_public": False,
        },
        service=drive,
        media_factory=lambda path: path,
    )

    host.host("hash-id", [f])

    names = {item["name"] for item in drive.store.values()}
    assert "FolderSync" not in names  # exact ID bypasses root lookup/creation
    assert {"Gotowe do sklepu", "Friendly Product", "model.stl"} <= names
    inbox = next(item for item in drive.store.values() if item["name"] == "Gotowe do sklepu")
    assert inbox["parent"] == "exact-user-folder-id"
    assert drive.public == set()


def test_update_existing_replaces_file_content_without_duplicate(tmp_path):
    f = tmp_path / "cover.png"
    f.write_bytes(b"first")
    drive = FakeDrive()
    settings = {"root_folder_name": "FolderSync", "update_existing": True}
    host = GoogleDriveHost(
        _config(), settings, service=drive, media_factory=lambda path: path
    )
    host.host("product", [f])
    count = len(drive.store)
    f.write_bytes(b"second")
    host.host("product", [f])

    assert len(drive.store) == count
    assert len(drive.updated) == 1


def test_relative_paths_preserve_nested_folders_and_duplicate_basenames(tmp_path):
    left = tmp_path / "left" / "part.stl"
    right = tmp_path / "right" / "part.stl"
    left.parent.mkdir()
    right.parent.mkdir()
    left.write_bytes(b"left")
    right.write_bytes(b"right")
    drive = FakeDrive()
    host = GoogleDriveHost(
        _config(),
        {
            "root_folder_id": "root-id",
            "relative_paths": {str(left): "left/part.stl", str(right): "right/part.stl"},
            "make_public": False,
        },
        service=drive,
        media_factory=lambda path: path,
    )

    urls = host.host("product", [left, right])

    assert set(urls) == {"left/part.stl", "right/part.stl"}
    names = [item["name"] for item in drive.store.values()]
    assert "left" in names and "right" in names
    assert names.count("part.stl") == 2
