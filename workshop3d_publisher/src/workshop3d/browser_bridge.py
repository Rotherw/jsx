"""Local, authenticated bridge between the publisher and Chrome extension.

The extension runs inside the user's normal Chrome profile, so it can reuse
tabs and already logged-in store sessions.  The publisher never receives or
copies browser cookies/passwords.  It only exposes queued jobs and their files
on 127.0.0.1, protected by a pairing key plus a per-job file token.
"""
from __future__ import annotations

import json
import mimetypes
import secrets
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import Config
from .models import ProductRecord, SocialResult, StoreResult


_STORE_BROWSER: dict[str, dict[str, Any]] = {
    "cults3d": {
        "target_url": "https://cults3d.com/en/upload",
        "success_hosts": ["cults3d.com"],
        "success_paths": ["/en/3d-model/", "/fr/modèle-3d/"],
    },
    "thangs": {
        "target_url": "https://thangs.com/mythangs/store",
        "success_hosts": ["thangs.com"],
        "success_paths": ["/designer/", "/3d-model/"],
    },
    "creality_cloud_eu": {
        "target_url": "https://www.crealitycloud.com/create-model-new?source=12",
        "success_hosts": ["www.crealitycloud.com", "crealitycloud.com"],
        "success_paths": ["/model-detail/"],
    },
    "creality_cloud_cn": {
        "target_url": "https://www.crealitycloud.cn/create-model-new?source=12",
        "success_hosts": ["www.crealitycloud.cn", "crealitycloud.cn"],
        "success_paths": ["/model-detail/"],
    },
}

_SOCIAL_BROWSER: dict[str, dict[str, Any]] = {
    "facebook": {
        "target_url": "https://www.facebook.com/",
        "success_hosts": ["www.facebook.com", "facebook.com"],
        "success_paths": ["/posts/", "/permalink/", "/photo/"],
    },
    "instagram": {
        "target_url": "https://www.instagram.com/",
        "success_hosts": ["www.instagram.com", "instagram.com"],
        "success_paths": ["/p/", "/reel/"],
    },
    "x": {
        "target_url": "https://x.com/compose/post",
        "success_hosts": ["x.com", "www.x.com", "twitter.com", "www.twitter.com"],
        "success_paths": ["/status/"],
    },
    "pinterest": {
        "target_url": "https://www.pinterest.com/pin-creation-tool/",
        "success_hosts": ["www.pinterest.com", "pinterest.com"],
        "success_paths": ["/pin/"],
    },
    "bluesky": {
        "target_url": "https://bsky.app/compose/post",
        "success_hosts": ["bsky.app"],
        "success_paths": ["/post/"],
    },
    "tiktok": {
        "target_url": "https://www.tiktok.com/upload",
        "success_hosts": ["www.tiktok.com", "tiktok.com"],
        "success_paths": ["/video/"],
    },
    "youtube": {
        "target_url": "https://www.youtube.com/",
        "success_hosts": ["www.youtube.com", "youtube.com"],
        "success_paths": ["/post/"],
    },
    "mastodon": {
        "target_url": "https://mastodon.social/publish",
        "success_hosts": ["mastodon.social"],
        "success_paths": ["/@"],
    },
}

_ACTIVE_JOB_STATES = {"QUEUED", "CLAIMED", "READY_FOR_REVIEW", "SUBMITTED"}
_RESULT_STATES = {
    "READY_FOR_REVIEW",
    "SUBMITTED",
    "PUBLISHED",
    "POSTED",
    "NEEDS_ATTENTION",
    "FAILED",
}
_MODEL_EXTENSIONS = {".stl", ".3mf", ".glb", ".obj", ".ply", ".off", ".zip"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class BrowserBridge:
    """Persistent job queue shared by adapters and the Flask dashboard."""

    _instances: dict[str, "BrowserBridge"] = {}
    _instances_lock = threading.Lock()

    @classmethod
    def shared(cls, config: Config) -> "BrowserBridge":
        path = _state_path(config)
        key = str(path.resolve())
        with cls._instances_lock:
            bridge = cls._instances.get(key)
            if bridge is None:
                bridge = cls(config, path)
                cls._instances[key] = bridge
            return bridge

    def __init__(self, config: Config, path: Path | None = None):
        self.config = config
        self.path = path or _state_path(config)
        self._lock = threading.RLock()
        self._data = self._load()
        self._server_url = str(
            config.get("browser.server_url", "http://127.0.0.1:5000")
        ).rstrip("/")

    @property
    def pairing_key(self) -> str:
        return str(self._data["pairing_key"])

    def set_server_url(self, url: str) -> None:
        self._server_url = url.rstrip("/")

    def is_authorized(self, supplied: str | None) -> bool:
        return bool(supplied) and secrets.compare_digest(str(supplied), self.pairing_key)

    def status(self) -> dict[str, Any]:
        with self._lock:
            heartbeat = float(self._data.get("last_heartbeat", 0.0) or 0.0)
            age = time.time() - heartbeat if heartbeat else None
            return {
                "connected": age is not None and age < 45,
                "last_seen_seconds": round(age, 1) if age is not None else None,
                "extension_version": self._data.get("extension_version"),
                "open_stores": list(self._data.get("open_stores", []) or []),
                "pairing_key": self.pairing_key,
                "pending_jobs": sum(
                    1 for j in self._data.get("jobs", {}).values()
                    if j.get("status") in _ACTIVE_JOB_STATES
                ),
            }

    def heartbeat(
        self,
        version: str = "",
        open_stores: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._data["last_heartbeat"] = time.time()
            if version:
                self._data["extension_version"] = str(version)[:40]
            if open_stores is not None:
                allowed = set(_STORE_BROWSER)
                self._data["open_stores"] = sorted(
                    {
                        str(store)
                        for store in open_stores
                        if str(store) in allowed
                    }
                )
            self._save()
            return self.status()

    def queue_store_job(
        self,
        platform: str,
        record: ProductRecord,
        workspace: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        spec = _STORE_BROWSER.get(platform)
        if spec is None:
            raise ValueError(f"Browser publishing is not configured for {platform}.")

        files = _collect_files(Path(workspace), platform)
        if not any(f["kind"] == "model" for f in files):
            raise ValueError("Nie znaleziono pliku modelu do wgrania w formularzu sklepu.")
        if not any(f["kind"] == "image" for f in files):
            raise ValueError("Nie znaleziono grafiki produktu do wgrania w formularzu sklepu.")

        with self._lock:
            # One active job per product/store. Retrying the pipeline must not
            # open duplicate forms in multiple tabs.
            for job in self._data.get("jobs", {}).values():
                if (
                    job.get("product_id") == record.product_id
                    and job.get("platform") == platform
                    and job.get("status") in _ACTIVE_JOB_STATES
                ):
                    return job

            job_id = secrets.token_urlsafe(12)
            price = record.metadata.get("PRICE", {}) or {}
            job = {
                "id": job_id,
                "product_id": record.product_id,
                "platform": platform,
                "status": "QUEUED",
                "created_at": time.time(),
                "updated_at": time.time(),
                "claimed_at": None,
                "file_token": secrets.token_urlsafe(24),
                "target_url": spec["target_url"],
                "success_hosts": list(spec["success_hosts"]),
                "success_paths": list(spec["success_paths"]),
                "auto_submit": bool(
                    settings.get(
                        "browser_auto_submit",
                        self.config.get("browser.auto_submit", False),
                    )
                ),
                "publish_as": settings.get("publish_as", "draft"),
                "metadata": {
                    "title": record.metadata.get("TITLE", record.folder_name),
                    "description": record.metadata.get("DESCRIPTION_EN", ""),
                    "short_description": record.metadata.get("SHORT_DESCRIPTION", ""),
                    "tags": list(record.metadata.get("TAGS", []) or []),
                    "category": record.metadata.get("CATEGORY", ""),
                    "price": price.get("amount", ""),
                    "currency": price.get("currency", "USD"),
                    "made_with_ai": bool(record.metadata.get("MADE_WITH_AI", False)),
                    "license": record.metadata.get("LICENSE_SUMMARY", {}),
                },
                "files": files,
                "result": {},
            }
            self._data.setdefault("jobs", {})[job_id] = job
            self._trim_jobs()
            self._save()
            return job

    def queue_social_job(
        self,
        platform: str,
        record: ProductRecord,
        workspace: str,
        text: str,
        product_url: str,
    ) -> dict[str, Any]:
        spec = _SOCIAL_BROWSER.get(platform)
        if spec is None:
            raise ValueError(f"Publikowanie w Chrome nie jest skonfigurowane dla {platform}.")
        files = _collect_social_files(Path(workspace))
        with self._lock:
            for job in self._data.get("jobs", {}).values():
                if (
                    job.get("kind") == "social"
                    and job.get("product_id") == record.product_id
                    and job.get("platform") == platform
                    and job.get("status") in _ACTIVE_JOB_STATES
                ):
                    return job

            job_id = secrets.token_urlsafe(12)
            job = {
                "id": job_id,
                "kind": "social",
                "product_id": record.product_id,
                "platform": platform,
                "status": "QUEUED",
                "created_at": time.time(),
                "updated_at": time.time(),
                "claimed_at": None,
                "file_token": secrets.token_urlsafe(24),
                "target_url": spec["target_url"],
                "success_hosts": list(spec["success_hosts"]),
                "success_paths": list(spec["success_paths"]),
                "auto_submit": True,
                "publish_as": "public",
                "metadata": {
                    "title": record.metadata.get("TITLE", record.folder_name),
                    "body": text,
                    "product_url": product_url,
                },
                "files": files,
                "result": {},
            }
            self._data.setdefault("jobs", {})[job_id] = job
            self._trim_jobs()
            self._save()
            return job

    def claim_next(self, server_url: str | None = None) -> dict[str, Any] | None:
        """Claim one queued/stale job and return the extension-safe payload."""
        with self._lock:
            now = time.time()
            jobs = sorted(
                self._data.get("jobs", {}).values(),
                key=lambda item: float(item.get("created_at", 0.0)),
            )
            chosen = None
            for job in jobs:
                status = job.get("status")
                stale_claim = (
                    status == "CLAIMED"
                    and now - float(job.get("claimed_at") or 0.0) > 120
                )
                if status == "QUEUED" or stale_claim:
                    chosen = job
                    break
            if chosen is None:
                return None
            chosen["status"] = "CLAIMED"
            chosen["claimed_at"] = now
            chosen["updated_at"] = now
            self._save()
            return self._public_job(chosen, server_url or self._server_url)

    def job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._data.get("jobs", {}).get(job_id)

    def record_result(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job = self._data.get("jobs", {}).get(job_id)
            if job is None:
                raise KeyError(job_id)
            status = str(payload.get("status", "FAILED")).upper()
            if status not in _RESULT_STATES:
                status = "FAILED"
            url = str(payload.get("url", "") or "")[:2000]
            message = str(payload.get("message", "") or "")[:3000]

            # A store is only "published" when the browser reached a listing
            # URL belonging to the expected store.  Filling/clicking alone is
            # never reported as a successful sale listing.
            completed_status = "POSTED" if job.get("kind") == "social" else "PUBLISHED"
            if status == completed_status and not _is_success_url(job, url):
                status = "NEEDS_ATTENTION"
                message = (
                    "Chrome zgłosił zakończenie, ale nie rozpoznano adresu gotowej publikacji. "
                    "Sprawdź kartę strony."
                )

            job["status"] = status
            job["updated_at"] = time.time()
            job["result"] = {"status": status, "url": url, "message": message}
            self._save()
            return job

    def file_for(self, job_id: str, index: int, token: str | None) -> tuple[Path, str]:
        with self._lock:
            job = self._data.get("jobs", {}).get(job_id)
            if job is None or not token or not secrets.compare_digest(token, job["file_token"]):
                raise KeyError(job_id)
            files = job.get("files", [])
            if index < 0 or index >= len(files):
                raise IndexError(index)
            path = Path(files[index]["path"])
            if not path.is_file():
                raise FileNotFoundError(path)
            return path, str(files[index].get("mime") or "application/octet-stream")

    def as_store_result(self, job: dict[str, Any]) -> StoreResult:
        status_map = {
            "QUEUED": "BROWSER_QUEUED",
            "CLAIMED": "BROWSER_QUEUED",
            "READY_FOR_REVIEW": "READY_FOR_REVIEW",
            "SUBMITTED": "SUBMITTED",
            "PUBLISHED": "PUBLISHED",
            "NEEDS_ATTENTION": "NEEDS_ATTENTION",
            "FAILED": "FAILED",
        }
        result = job.get("result", {}) or {}
        status = status_map.get(job.get("status"), "BROWSER_QUEUED")
        default_message = (
            "Zadanie przekazane do Chrome. Rozszerzenie użyje zalogowanej karty "
            "i wypełni formularz."
        )
        return StoreResult(
            platform=str(job["platform"]),
            status=status,
            listing_id=str(job["id"]),
            url=result.get("url") or job.get("target_url"),
            message=result.get("message") or default_message,
        )

    def as_social_result(self, job: dict[str, Any]) -> SocialResult:
        status_map = {
            "QUEUED": "BROWSER_QUEUED",
            "CLAIMED": "BROWSER_QUEUED",
            "READY_FOR_REVIEW": "READY_FOR_REVIEW",
            "SUBMITTED": "SUBMITTED",
            "POSTED": "POSTED",
            "NEEDS_ATTENTION": "NEEDS_ATTENTION",
            "FAILED": "FAILED",
        }
        result = job.get("result", {}) or {}
        return SocialResult(
            platform=str(job["platform"]),
            status=status_map.get(job.get("status"), "BROWSER_QUEUED"),
            post_url=result.get("url"),
            message=result.get("message") or "Post przekazany do zalogowanej karty Chrome.",
        )

    def _public_job(self, job: dict[str, Any], server_url: str) -> dict[str, Any]:
        base = server_url.rstrip("/")
        files = []
        for index, item in enumerate(job.get("files", [])):
            files.append({
                "name": item["name"],
                "kind": item["kind"],
                "mime": item["mime"],
                "url": (
                    f"{base}/api/browser/jobs/{job['id']}/files/{index}"
                    f"?token={job['file_token']}"
                ),
            })
        return {
            "id": job["id"],
            "kind": job.get("kind", "store"),
            "product_id": job["product_id"],
            "platform": job["platform"],
            "target_url": job["target_url"],
            "success_hosts": job["success_hosts"],
            "success_paths": job["success_paths"],
            "auto_submit": job["auto_submit"],
            "publish_as": job["publish_as"],
            "metadata": job["metadata"],
            "files": files,
        }

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and loaded.get("pairing_key"):
                    loaded.setdefault("jobs", {})
                    return loaded
            except (OSError, ValueError, TypeError):
                pass
        data = {"pairing_key": secrets.token_urlsafe(32), "jobs": {}}
        # Persist lazily on the first heartbeat/job. Merely opening a settings
        # page (or constructing a test app) should not create runtime files.
        return data

    def _save(self) -> None:
        self._write_data(self._data)

    def _write_data(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def _trim_jobs(self) -> None:
        jobs = self._data.get("jobs", {})
        if len(jobs) <= 100:
            return
        removable = sorted(
            (j for j in jobs.values() if j.get("status") not in _ACTIVE_JOB_STATES),
            key=lambda item: float(item.get("updated_at", 0.0)),
        )
        for job in removable[: max(0, len(jobs) - 100)]:
            jobs.pop(job["id"], None)


def queue_browser_publish(
    config: Config,
    settings: dict[str, Any],
    platform: str,
    record: ProductRecord,
    workspace: str,
) -> StoreResult:
    """Adapter convenience wrapper returning an honest StoreResult."""
    bridge = BrowserBridge.shared(config)
    try:
        job = bridge.queue_store_job(platform, record, workspace, settings)
    except (OSError, ValueError) as exc:
        return StoreResult(platform=platform, status="NEEDS_ATTENTION", message=str(exc))
    return bridge.as_store_result(job)


def queue_browser_social(
    config: Config,
    platform: str,
    record: ProductRecord,
    workspace: str,
    text: str,
    product_url: str,
) -> SocialResult:
    bridge = BrowserBridge.shared(config)
    try:
        job = bridge.queue_social_job(
            platform, record, workspace, text, product_url
        )
    except (OSError, ValueError) as exc:
        return SocialResult(platform=platform, status="NEEDS_ATTENTION", message=str(exc))
    return bridge.as_social_result(job)


def _state_path(config: Config) -> Path:
    configured = config.get("browser.state_file", "")
    return Path(configured) if configured else config.work_folder / "browser_bridge.json"


def _collect_files(workspace: Path, platform: str) -> list[dict[str, str]]:
    candidates: list[tuple[Path, str]] = []
    files_dir = workspace / "files"
    media_dir = workspace / "media"
    package_dir = workspace / "package"

    if files_dir.exists():
        candidates.extend(
            (p, "model") for p in sorted(files_dir.iterdir())
            if p.is_file() and p.suffix.lower() in _MODEL_EXTENSIONS
        )
    if platform == "cults3d" and package_dir.exists():
        # Cults accepts a package; prefer it in addition to source formats.
        candidates.extend(
            (p, "model") for p in sorted(package_dir.glob("*.zip")) if p.is_file()
        )

    image_source = media_dir if media_dir.exists() else files_dir
    if image_source.exists():
        candidates.extend(
            (p, "image") for p in sorted(image_source.iterdir())
            if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS
        )

    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for path, kind in candidates:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        result.append({"path": resolved, "name": path.name, "kind": kind, "mime": mime})
    return result


def _collect_social_files(workspace: Path) -> list[dict[str, str]]:
    result = _collect_files(workspace, "social")
    for directory in (workspace / "files", workspace / "media"):
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in {".mp4", ".mov", ".webm"}:
                continue
            resolved = str(path.resolve())
            if any(item["path"] == resolved for item in result):
                continue
            result.append({
                "path": resolved,
                "name": path.name,
                "kind": "video",
                "mime": mimetypes.guess_type(path.name)[0] or "video/mp4",
            })
    # Models are never uploaded to a social composer.
    return [item for item in result if item["kind"] in {"image", "video"}]


def _is_success_url(job: dict[str, Any], url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    allowed_hosts = {str(h).lower() for h in job.get("success_hosts", [])}
    if parsed.scheme != "https" or host not in allowed_hosts:
        return False
    if job.get("kind") == "social":
        # For social composers the trusted extension reports POSTED only after
        # the site's confirmation UI. Several sites keep the home URL instead
        # of navigating to the new post, so the verified host is authoritative.
        return True
    paths = [str(p) for p in job.get("success_paths", [])]
    if job.get("platform") == "thangs":
        # Both fragments are required for a real Thangs model listing.
        return all(fragment in parsed.path for fragment in paths)
    return any(fragment in parsed.path for fragment in paths)
