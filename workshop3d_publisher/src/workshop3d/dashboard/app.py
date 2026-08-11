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

# How each network renders the product link in its post.
_LINK_MODE = {"instagram": "bio", "tiktok": "profile"}


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
        "DETECTED": "New product found.",
        "WAITING_FOR_REQUIRED_FILES": "Waiting for PNG and STL files.",
        "VALIDATING": "Checking files.",
        "PREPARING_PRODUCT": "Preparing the product.",
        "PREPARING_MEDIA": "Preparing graphics.",
        "READY_TO_PUBLISH": "Ready to publish.",
        "AWAITING_APPROVAL": "Czeka na Twoja akceptacje - sprawdz podglad.",
        "AWAITING_BROWSER_REVIEW": "Chrome: formularz czeka na sprawdzenie lub publikację.",
        "PUBLISHING": "Publishing to stores.",
        "PUBLISHED": "Published in at least one store.",
        "PROMOTING": "Posting to social media.",
        "COMPLETED": "Done - everything succeeded.",
        "COMPLETED_WITH_WARNINGS": "Done, but some steps need a look.",
        "NEEDS_ATTENTION": "Needs your attention.",
        "FAILED": "Failed. You can retry.",
    }

    @app.route("/")
    def index():
        products = []
        for r in store.all():
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
            })
        return render_template(
            "index.html",
            products=products,
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
        config.set("modes.dry_run", _bool("dry_run"))
        config.set("modes.auto_publish", _bool("auto_publish"))
        config.set("modes.require_approval", _bool("require_approval"))
        config.set("brand.render_graphics", _bool("render_graphics"))
        config.set("brand.logo_path", f.get("brand_logo_path", "").strip())
        config.set("brand.patron_name", f.get("brand_patron_name", "KF2.pl").strip() or "KF2.pl")
        config.set("brand.patron_logo_path", f.get("brand_patron_logo_path", "").strip())
        config.set("brand.font_path", f.get("brand_font_path", "").strip())
        config.set("content.made_with_ai", _bool("made_with_ai"))
        config.set("wiki.enabled", _bool("wiki_enabled"))
        config.set("wiki.base_url", f.get("wiki_base_url", "https://wiki.kf2.pl").strip())
        config.set("browser.auto_submit", _bool("browser_auto_submit"))
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
        config.set("asset_hosts.google_drive.root_folder_name",
                   f.get("gdrive_root_folder", "FolderSync").strip() or "FolderSync")

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
