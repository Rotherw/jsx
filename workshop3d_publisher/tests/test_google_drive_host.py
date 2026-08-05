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


class FakePermissions:
    def __init__(self, drive): self.drive = drive
    def create(self, fileId=None, body=None):
        self.drive.public.add(fileId)
        return _Exec({"id": "perm"})


class FakeDrive:
    def __init__(self):
        self.store = {}
        self.public = set()
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
