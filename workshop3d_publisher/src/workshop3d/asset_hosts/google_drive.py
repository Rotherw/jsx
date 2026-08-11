"""Google Drive asset host.

Uploads a product's images and package into a "FolderSync" folder on Google
Drive, marks them public, and returns direct-download URLs in the form Cults3D
accepts (the URL exposes the filename + extension via a `filename=` parameter).

Authentication uses a Google **service account** (best for unattended runs):
the JSON key path is read from an environment variable (default
GOOGLE_APPLICATION_CREDENTIALS) and the FolderSync folder must be shared with
the service account's e-mail. No secret is ever written to config or logs.

The Google client libraries are imported lazily so the rest of the system runs
and tests without them. The Drive service is injectable for testing.
"""
from __future__ import annotations

import os
from pathlib import Path

from .base import AssetHost, AssetHostError, register_host

_DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


def _q_escape(name: str) -> str:
    return name.replace("\\", "\\\\").replace("'", "\\'")


def _build_drive_service(settings: dict):
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as exc:
        raise AssetHostError(
            "Google Drive libraries are not installed. Run: "
            "pip install google-api-python-client google-auth"
        ) from exc

    env_name = settings.get("credentials_env", "GOOGLE_APPLICATION_CREDENTIALS")
    cred_path = os.environ.get(env_name)
    if not cred_path or not os.path.exists(cred_path):
        raise AssetHostError(
            f"Set {env_name} to the path of your Google service-account JSON key, "
            "and share the FolderSync folder with that service account's e-mail."
        )
    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


@register_host
class GoogleDriveHost(AssetHost):
    key = "google_drive"

    def __init__(self, config, settings: dict, service=None, media_factory=None):
        super().__init__(config, settings)
        self._service = service              # injectable for tests
        self._media_factory = media_factory  # injectable for tests
        self._folder_cache: dict[str, str] = {}

    def _svc(self):
        if self._service is None:
            self._service = _build_drive_service(self.settings)
        return self._service

    # -- public API ---------------------------------------------------------
    def host(self, product_id: str, paths: list[Path]) -> dict[str, str]:
        if not paths:
            return {}
        svc = self._svc()
        root_name = self.settings.get("root_folder_name", "FolderSync")
        root_id = self.settings.get("root_folder_id") or self._folder(svc, root_name, parent=None)
        parent_id = root_id
        for name in self.settings.get("parent_folder_names", []) or []:
            if str(name).strip():
                parent_id = self._folder(svc, str(name).strip(), parent=parent_id)
        product_name = str(self.settings.get("product_folder_name") or product_id)
        sub_id = self._folder(svc, product_name, parent=parent_id)
        relative_paths = self.settings.get("relative_paths", {}) or {}

        urls: dict[str, str] = {}
        for p in paths:
            relative = Path(str(relative_paths.get(str(p), p.name)).replace("\\", "/"))
            file_parent = sub_id
            for part in relative.parts[:-1]:
                file_parent = self._folder(svc, part, parent=file_parent)
            file_name = relative.name or p.name
            file_id = self._upload_or_find(svc, file_parent, p, name=file_name)
            if self.settings.get("make_public", True):
                self._make_public(svc, file_id)
            key = relative.as_posix()
            urls[key] = self._download_url(file_id, file_name)
        return urls

    # -- Drive helpers ------------------------------------------------------
    def _folder(self, svc, name: str, parent: str | None) -> str:
        cache_key = f"{parent or 'root'}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        q = (f"mimeType='{_DRIVE_FOLDER_MIME}' and name='{_q_escape(name)}' "
             "and trashed=false")
        if parent:
            q += f" and '{parent}' in parents"
        res = svc.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
        items = res.get("files", [])
        if items:
            fid = items[0]["id"]
        else:
            meta = {"name": name, "mimeType": _DRIVE_FOLDER_MIME}
            if parent:
                meta["parents"] = [parent]
            fid = svc.files().create(body=meta, fields="id").execute()["id"]
        self._folder_cache[cache_key] = fid
        return fid

    def _upload_or_find(
        self, svc, folder_id: str, path: Path, name: str | None = None
    ) -> str:
        # Idempotent: reuse an existing file with the same name in this folder.
        remote_name = name or path.name
        q = f"name='{_q_escape(remote_name)}' and '{folder_id}' in parents and trashed=false"
        res = svc.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
        items = res.get("files", [])
        if items:
            file_id = items[0]["id"]
            if self.settings.get("update_existing", False):
                media = self._make_media(str(path))
                svc.files().update(fileId=file_id, media_body=media).execute()
            return file_id

        media = self._make_media(str(path))
        created = svc.files().create(
            body={"name": remote_name, "parents": [folder_id]},
            media_body=media, fields="id",
        ).execute()
        return created["id"]

    def _make_media(self, path: str):
        if self._media_factory is not None:
            return self._media_factory(path)
        try:
            from googleapiclient.http import MediaFileUpload  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise AssetHostError("google-api-python-client is required to upload.") from exc
        return MediaFileUpload(path, resumable=True)

    def _make_public(self, svc, file_id: str) -> None:
        try:
            svc.permissions().create(
                fileId=file_id, body={"role": "reader", "type": "anyone"},
            ).execute()
        except Exception:
            # Already public, or permission already exists -> fine.
            pass

    def _download_url(self, file_id: str, filename: str) -> str:
        template = self.settings.get("url_template", "usercontent")
        if template == "uc":
            return (f"https://drive.google.com/uc?export=download"
                    f"&id={file_id}&filename={filename}")
        return (f"https://drive.usercontent.google.com/download"
                f"?id={file_id}&export=download&confirm=t&filename={filename}")
