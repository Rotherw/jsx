"""Local status dashboard (spec section 21).

Plain-language product list, live state, working links, and buttons to:
  * retry a failed publication,
  * open a product's folder,
  * stop/start automatic publishing.

No terminal commands required for daily use.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, url_for

from ..config import Config, DEFAULT_CONFIG
from ..state_store import StateStore
from ..pipeline import Pipeline
from ..publication_manager import _store_tags, main_product_url
from ..adapters.base import compose_post
from .. import secrets_env
from ..automation import AutomationControl
from ..browser_bridge import BrowserBridge
from .. import cloud_inbox, cloud_mirror

# How each network renders the product link in its post.
_LINK_MODE = {"instagram": "bio", "tiktok": "profile"}

_DONE_STATES = {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
_ATTENTION_STATES = {"WAITING_FOR_REQUIRED_FILES", "NEEDS_ATTENTION", "FAILED"}
_PUBLISHED_STORE_STATES = {"PUBLISHED", "DRY_RUN"}
_FINAL_STORE_STATES = {"PUBLISHED", "FAILED", "NOT_CONNECTED", "NEEDS_ATTENTION"}
_STORE_LABELS = {
    "cults3d": "Cults3D",
    "thangs": "Thangs",
    "creality_cloud_eu": "Creality EU",
    "creality_cloud_cn": "Creality CN",
}


def _local_time(timestamp: float | None) -> str | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y, %H:%M:%S")


def _duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    if total < 60:
        return f"{total} s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes} min {secs:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def _progress_view(record, config) -> dict:
    total_steps = max(int(record.progress_total or 9), 1)
    current_step = min(max(int(record.progress_step or 0), 0), total_steps)
    enabled_stores = config.enabled_stores()
    published_stores = sum(
        result.get("status") in _PUBLISHED_STORE_STATES
        for name, result in record.stores.items()
        if name in enabled_stores
    )
    cloud_targets = (record.cloud_sync or {}).get("targets", {}) or {}
    archive_targets = (record.cloud_archive or {}).get("targets", {}) or {}
    archive_done = record.cloud_archive.get("status") == "ARCHIVED"
    cloud_enabled = bool(config.get("cloud_sync.enabled", False))
    return {
        "step": current_step,
        "steps": total_steps,
        "percent": round(current_step * 100 / total_steps),
        "stores_done": published_stores,
        "stores_total": len(enabled_stores),
        "finished_at": _local_time(record.completed_at),
        "updated_at": _local_time(record.updated_at),
        "duration": _duration(
            (record.completed_at or datetime.now().timestamp()) - record.detected_at
        ),
        "cloud_status": record.cloud_sync.get("status", "PENDING") if record.cloud_sync else "PENDING",
        "cloud_enabled": cloud_enabled,
        "cloud_done": (
            not cloud_enabled
            or (record.cloud_sync.get("status") == "SYNCED" and archive_done)
        ),
        "cloud_message": record.cloud_sync.get("message"),
        "google_sync": cloud_targets.get("google_drive", {}),
        "nextcloud_sync": cloud_targets.get("nextcloud", {}),
        "archive_status": record.cloud_archive.get("status", "PENDING"),
        "archive_done": archive_done,
        "archive_message": record.cloud_archive.get("message"),
        "google_archive": archive_targets.get("google_drive", {}),
        "nextcloud_archive": archive_targets.get("nextcloud", {}),
    }


def _statistics(records, config) -> tuple[dict, list[dict]]:
    today = datetime.now().date()
    completed = [r for r in records if r.state in _DONE_STATES]
    durations = [
        r.completed_at - r.detected_at
        for r in completed
        if r.completed_at is not None and r.completed_at >= r.detected_at
    ]
    store_results = [result for r in records for result in r.stores.values()]
    published = sum(result.get("status") == "PUBLISHED" for result in store_results)
    final_results = [r for r in store_results if r.get("status") in _FINAL_STORE_STATES]
    success_rate = round(published * 100 / len(final_results)) if final_results else None

    summary = {
        "all": len(records),
        "done": len(completed),
        "today_done": sum(
            r.completed_at is not None
            and datetime.fromtimestamp(r.completed_at).date() == today
            for r in completed
        ),
        "published": published,
        "cloud_synced": sum(
            r.cloud_sync.get("status") == "SYNCED"
            and r.cloud_archive.get("status") == "ARCHIVED"
            for r in records
        ),
        "success_rate": f"{success_rate}%" if success_rate is not None else "—",
        "average_duration": _duration(sum(durations) / len(durations)) if durations else "—",
        "attention": sum(r.state in _ATTENTION_STATES for r in records),
    }
    summary["running"] = summary["all"] - summary["done"] - summary["attention"]

    platforms = list(config.enabled_stores())
    platforms.extend(
        platform
        for r in records
        for platform in r.stores
        if platform not in platforms
    )
    per_store = []
    for platform in platforms:
        results = [r.stores[platform] for r in records if platform in r.stores]
        real_final = [item for item in results if item.get("status") in _FINAL_STORE_STATES]
        successes = sum(item.get("status") == "PUBLISHED" for item in results)
        per_store.append({
            "name": _STORE_LABELS.get(platform, platform),
            "published": successes,
            "attempts": len(real_final),
            "errors": sum(
                item.get("status") in {"FAILED", "NOT_CONNECTED", "NEEDS_ATTENTION"}
                for item in results
            ),
        })
    return summary, per_store


def _build_preview(record, config):
    """Compute exactly what would be sent: listing + per-network post text."""
    meta = record.metadata or {}
    # Store tags: real ones if published, else the enabled stores (best estimate).
    tags = _store_tags(record, config)
    if not tags:
        handles = config.get("social.store_handles", {}) or {}
        enabled = config.enabled_stores()
        seen = []
        for k in enabled:
            h = handles.get(k)
            if h and h not in seen:
                seen.append(h)
        tags = " ".join(seen)
    meta["ACTIVE_STORE_TAGS"] = tags

    product_url = main_product_url(record, config) or "[link pojawi sie po publikacji]"

    posts = []
    for net in config.enabled_social().keys():
        posts.append({
            "network": net,
            "text": compose_post(record, net, product_url, link_mode=_LINK_MODE.get(net, "url")),
        })
    return {"tags": tags, "product_url": product_url, "posts": posts}


def create_app(
    config: Config,
    store: StateStore,
    automation: AutomationControl | None = None,
    bridge: BrowserBridge | None = None,
    dashboard_port: int = 5000,
) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
    automation = automation or AutomationControl()
    bridge = bridge or BrowserBridge.shared(config)
    bridge.set_server_url(f"http://127.0.0.1:{dashboard_port}")

    @app.before_request
    def _block_cross_site_local_writes():
        # A random website must not be able to POST to the local dashboard and
        # turn publishing on. Extension endpoints have their own pairing-key
        # authentication and are excluded from this Origin check.
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if request.path.startswith("/api/browser/"):
            return None
        origin = request.headers.get("Origin")
        if not origin:  # non-browser clients/tests; no ambient web origin
            return None
        try:
            parsed = urlparse(origin)
        except ValueError:
            abort(403)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost"}:
            abort(403)
        return None

    @app.after_request
    def _local_file_cors(response):
        # Store-page scripts may need a Private Network Access preflight before
        # fetching a queued file from 127.0.0.1. The unguessable job token is
        # still validated on the actual GET.
        if request.path.startswith("/api/browser/jobs/") and "/files/" in request.path:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Private-Network"] = "true"
            response.headers["Cache-Control"] = "no-store"
        return response

    STATUS_TEXT = {
        "DETECTED": "Wykryto nowy produkt.",
        "WAITING_FOR_REQUIRED_FILES": "Czekam na komplet plików PNG i STL.",
        "VALIDATING": "Sprawdzam pliki.",
        "PREPARING_PRODUCT": "Przygotowuję produkt i opis.",
        "PREPARING_MEDIA": "Przygotowuję grafiki i paczkę.",
        "SYNCING_CLOUDS": "Synchronizuję Google Drive i Nextcloud.",
        "READY_TO_PUBLISH": "Produkt jest gotowy do wysłania.",
        "AWAITING_APPROVAL": "Czeka na ręczne zatwierdzenie.",
        "AWAITING_BROWSER_REVIEW": "Chrome kończy publikowanie w sklepach.",
        "AWAITING_CLOUD_SYNC": "Czekam na synchronizację obu chmur.",
        "PUBLISHING": "Wysyłam produkt do sklepów.",
        "PUBLISHED": "Oferta jest już w co najmniej jednym sklepie.",
        "PROMOTING": "Publikuję informacje w mediach społecznościowych.",
        "COMPLETED": "Gotowe — możesz sprawdzić produkt w sklepach.",
        "COMPLETED_WITH_WARNINGS": "Proces zakończony — część sklepów wymaga uwagi.",
        "NEEDS_ATTENTION": "Automat zatrzymał się i pokazuje przyczynę.",
        "FAILED": "Wystąpił błąd — możesz ponowić automatycznie.",
    }

    @app.route("/")
    def index():
        # The product currently being processed should always be at the top.
        records = list(reversed(store.all()))
        products = []
        for r in records:
            progress = _progress_view(r, config)
            products.append({
                "id": r.product_id,
                "name": r.metadata.get("TITLE", r.folder_name),
                "folder": r.folder_path,
                "state": r.state,
                "state_text": STATUS_TEXT.get(r.state, r.state),
                "main_link": r.main_link,
                "links": r.links,
                "action": r.required_user_action,
                "attempts": r.attempts,
                "file_count": len(r.png_files) + len(r.stl_files) + len(r.glb_files) + len(r.tmf_files),
                **progress,
            })
        summary, store_stats = _statistics(records, config)
        mirror = cloud_mirror.read_status(config)
        if mirror.get("last_sync_at"):
            mirror["last_sync_text"] = _local_time(mirror["last_sync_at"])
        inbox = cloud_inbox.read_status(config)
        if inbox.get("last_scan_at"):
            inbox["last_scan_text"] = _local_time(inbox["last_scan_at"])
        if inbox.get("last_product_at"):
            inbox["last_product_text"] = _local_time(inbox["last_product_at"])
        return render_template(
            "index.html",
            products=products,
            summary=summary,
            store_stats=store_stats,
            mirror=mirror,
            inbox=inbox,
            dry_run=config.dry_run,
            auto_publish=config.auto_publish,
            automation=automation.enabled,
            browser=bridge.status(),
        )

    @app.route("/api/products")
    def api_products():
        return jsonify([r.to_dict() for r in store.all()])

    @app.route("/product/<product_id>")
    def product(product_id: str):
        record = store.get(product_id)
        if not record:
            abort(404)
        preview = _build_preview(record, config)
        media_names = []
        if record.package_path:
            media_dir = Path(record.package_path) / "media"
            if media_dir.exists():
                media_names = [p.name for p in sorted(media_dir.glob("*.png"))]
        return render_template(
            "product.html",
            r=record,
            meta=record.metadata or {},
            preview=preview,
            media_names=media_names,
            awaiting=record.state in ("AWAITING_APPROVAL", "READY_TO_PUBLISH"),
            browser_waiting=record.state == "AWAITING_BROWSER_REVIEW",
            state_text=STATUS_TEXT.get(record.state, record.state),
            progress=_progress_view(record, config),
        )

    @app.route("/product/<product_id>/media/<name>")
    def product_media(product_id: str, name: str):
        record = store.get(product_id)
        if not record or not record.package_path:
            abort(404)
        media_dir = (Path(record.package_path) / "media").resolve()
        target = (media_dir / name).resolve()
        # Prevent path traversal: the file must live inside the media dir.
        if not str(target).startswith(str(media_dir)) or not target.is_file():
            abort(404)
        return send_file(target)

    @app.route("/publish/<product_id>", methods=["POST"])
    def publish_now(product_id: str):
        record = store.get(product_id)
        if record and record.state in ("AWAITING_APPROVAL", "READY_TO_PUBLISH", "NEEDS_ATTENTION"):
            Pipeline(config, store).publish_now(record)
        return redirect(url_for("product", product_id=product_id))

    @app.route("/retry/<product_id>", methods=["POST"])
    def retry(product_id: str):
        record = store.get(product_id)
        if record:
            Pipeline(config, store).run(record)
        return redirect(url_for("index"))

    @app.route("/open/<product_id>", methods=["POST"])
    def open_folder(product_id: str):
        record = store.get(product_id)
        if record and Path(record.folder_path).exists():
            _open_in_file_manager(record.folder_path)
        return redirect(url_for("index"))

    @app.route("/toggle-automation", methods=["POST"])
    def toggle_automation():
        automation.toggle()
        return redirect(url_for("index"))

    # -- Paired Chrome bridge --------------------------------------------
    def _browser_authorized() -> bool:
        return bridge.is_authorized(request.headers.get("X-WorkShop3D-Key"))

    @app.route("/api/browser/heartbeat", methods=["POST"])
    def browser_heartbeat():
        if not _browser_authorized():
            abort(401)
        payload = request.get_json(silent=True) or {}
        status = bridge.heartbeat(str(payload.get("version", "")))
        return jsonify({k: v for k, v in status.items() if k != "pairing_key"})

    @app.route("/api/browser/jobs/next")
    def browser_next_job():
        if not _browser_authorized():
            abort(401)
        job = bridge.claim_next(request.host_url.rstrip("/"))
        if job is None:
            return "", 204
        return jsonify(job)

    @app.route("/api/browser/jobs/<job_id>/result", methods=["POST"])
    def browser_job_result(job_id: str):
        if not _browser_authorized():
            abort(401)
        payload = request.get_json(silent=True) or {}
        try:
            job = bridge.record_result(job_id, payload)
        except KeyError:
            abort(404)

        record = store.get(str(job["product_id"]))
        if record is not None:
            record.stores[str(job["platform"])] = bridge.as_store_result(job).__dict__
            Pipeline(config, store).resume_after_browser(record)
        return jsonify({"ok": True, "status": job["status"]})

    @app.route("/api/browser/jobs/<job_id>/files/<int:index>")
    def browser_job_file(job_id: str, index: int):
        # Page scripts cannot add our private header to a file input fetch, so
        # this endpoint uses a separate, unguessable per-job token.
        try:
            path, mime = bridge.file_for(job_id, index, request.args.get("token"))
        except (KeyError, IndexError, FileNotFoundError):
            abort(404)
        response = send_file(path, mimetype=mime, download_name=path.name)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/browser/install", methods=["POST"])
    def browser_install():
        extension_dir = Path(__file__).resolve().parents[3] / "browser_extension"
        _open_in_file_manager(str(extension_dir))
        _open_chrome_extensions()
        return redirect(url_for("settings", browser_install="1"))

    # -- Settings (no YAML/code editing) -----------------------------------
    env_path = DEFAULT_CONFIG.parent / ".env"

    @app.route("/settings")
    def settings():
        secret_status = {k: secrets_env.is_set(k) for k in secrets_env.KNOWN_SECRETS}
        return render_template(
            "settings.html",
            c=config,
            secret_status=secret_status,
            saved=request.args.get("saved"),
            browser_install=request.args.get("browser_install"),
            browser=bridge.status(),
        )

    @app.route("/settings", methods=["POST"])
    def save_settings():
        f = request.form

        def _bool(name): return f.get(name) in ("on", "true", "1", "yes")

        # Paths + modes + trigger.
        config.set("paths.ready_folder", f.get("ready_folder", "").strip())
        config.set("paths.work_folder", f.get("work_folder", "").strip() or "work")
        zero_touch = _bool("zero_touch")
        config.set("modes.zero_touch", zero_touch)
        if zero_touch:
            config.set("modes.dry_run", False)
            config.set("modes.auto_publish", True)
            config.set("modes.require_approval", False)
            config.set("browser.auto_submit", True)
        else:
            config.set("modes.dry_run", _bool("dry_run"))
            config.set("modes.auto_publish", _bool("auto_publish"))
            config.set("modes.require_approval", _bool("require_approval"))
            config.set("browser.auto_submit", _bool("browser_auto_submit"))
        config.set("brand.render_graphics", _bool("render_graphics"))
        config.set("brand.logo_path", f.get("brand_logo_path", "").strip())
        config.set("brand.patron_name", f.get("brand_patron_name", "KF2.pl").strip() or "KF2.pl")
        config.set("brand.patron_logo_path", f.get("brand_patron_logo_path", "").strip())
        config.set("brand.font_path", f.get("brand_font_path", "").strip())
        config.set("content.made_with_ai", _bool("made_with_ai"))
        config.set("wiki.enabled", _bool("wiki_enabled"))
        config.set("wiki.base_url", f.get("wiki_base_url", "https://wiki.kf2.pl").strip())
        try:
            config.set("trigger.stability_delay_seconds", int(f.get("stability_delay_seconds", "60")))
        except ValueError:
            pass

        # Stores.
        config.set("stores.cults3d.enabled", _bool("cults3d_enabled"))
        config.set("stores.cults3d.mode", f.get("cults3d_mode", "browser"))
        config.set("stores.cults3d.publish_as", f.get("cults3d_publish_as", "public"))
        config.set("stores.cults3d.asset_host", f.get("cults3d_asset_host", "google_drive"))
        config.set("stores.cults3d.license_code", f.get("cults3d_license_code", "").strip())
        config.set("stores.thangs.enabled", _bool("thangs_enabled"))
        config.set("stores.thangs.mode", f.get("thangs_mode", "browser"))
        config.set("stores.thangs.publish_as", f.get("thangs_publish_as", "public"))
        config.set("stores.thangs.sync_folder", f.get("thangs_sync_folder", "").strip())
        config.set("stores.creality_cloud_eu.enabled", _bool("creality_eu_enabled"))
        config.set("stores.creality_cloud_eu.mode", f.get("creality_eu_mode", "browser"))
        config.set("stores.creality_cloud_eu.publish_as", f.get("creality_eu_publish_as", "public"))
        config.set("stores.creality_cloud_eu.staging_folder", f.get("creality_eu_staging_folder", "").strip())
        config.set("stores.creality_cloud_cn.enabled", _bool("creality_cn_enabled"))
        config.set("stores.creality_cloud_cn.mode", f.get("creality_cn_mode", "browser"))
        config.set("stores.creality_cloud_cn.publish_as", f.get("creality_cn_publish_as", "public"))
        config.set("stores.creality_cloud_cn.staging_folder", f.get("creality_cn_staging_folder", "").strip())
        config.set(
            "cloud_sync.enabled",
            True if zero_touch else _bool("cloud_sync_enabled"),
        )
        config.set(
            "cloud_sync.mirror_enabled",
            True if zero_touch else _bool("cloud_mirror_enabled"),
        )
        config.set("cloud_sync.inbox_folder",
                   f.get("cloud_inbox_folder",
                         str(config.get("cloud_sync.inbox_folder", "Gotowe do sklepu"))).strip()
                   or "Gotowe do sklepu")
        config.set("cloud_sync.published_folder",
                   f.get("cloud_published_folder",
                         str(config.get("cloud_sync.published_folder", "Opublikowane"))).strip()
                   or "Opublikowane")
        config.set("cloud_sync.google_drive.folder_name",
                   f.get("gdrive_root_folder", "FolderSync").strip() or "FolderSync")
        config.set("cloud_sync.google_drive.folder_id",
                   f.get("gdrive_folder_id", "").strip())
        config.set("cloud_sync.google_drive.local_folder",
                   f.get("google_sync_local_folder", "").strip())
        config.set("cloud_sync.nextcloud.server_url",
                   f.get("nextcloud_server_url", "https://cloud.workshop3d.pl").strip())
        config.set("cloud_sync.nextcloud.folder_path",
                   f.get("nextcloud_folder_path", "Folder Sync").strip() or "Folder Sync")
        config.set("cloud_sync.nextcloud.local_folder",
                   f.get("nextcloud_sync_local_folder", "").strip())

        # Social networks (enable toggles).
        for net in ("facebook", "instagram", "x", "pinterest", "mastodon", "bluesky"):
            config.set(f"social.{net}.enabled", _bool(f"social_{net}_enabled"))

        config.save()      # writes config.yaml (updates in-memory too)

        # Secrets -> local .env (only non-empty values overwrite; blanks ignored
        # unless the user ticked "clear").
        updates = {}
        for key in secrets_env.KNOWN_SECRETS:
            val = f.get(f"secret_{key}", "")
            if val.strip() or f.get(f"clear_{key}"):
                updates[key] = val
        if updates:
            secrets_env.save_secrets(env_path, updates)

        return redirect(url_for("settings", saved="1"))

    return app


def _open_in_file_manager(path: str) -> None:  # pragma: no cover
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        print(f"[dashboard] cannot open folder: {exc}")


def _open_chrome_extensions() -> None:  # pragma: no cover - Windows integration
    """Open chrome://extensions in the existing Chrome profile when possible."""
    if not sys.platform.startswith("win"):
        import webbrowser
        webbrowser.open("chrome://extensions")
        return
    candidates = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    for executable in candidates:
        if executable.is_file():
            subprocess.Popen([str(executable), "chrome://extensions"])
            return
    try:
        subprocess.Popen(["chrome.exe", "chrome://extensions"])
    except OSError as exc:
        print(f"[dashboard] cannot open Chrome extensions: {exc}")
