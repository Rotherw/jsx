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
import threading
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from ..config import Config, DEFAULT_CONFIG
from ..state_store import StateStore
from ..pipeline import Pipeline
from .. import secrets_env


def create_app(config: Config, store: StateStore) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
    app.config["W3D_AUTOMATION_ENABLED"] = True

    STATUS_TEXT = {
        "DETECTED": "New product found.",
        "WAITING_FOR_REQUIRED_FILES": "Waiting for PNG and STL files.",
        "VALIDATING": "Checking files.",
        "PREPARING_PRODUCT": "Preparing the product.",
        "PREPARING_MEDIA": "Preparing graphics.",
        "READY_TO_PUBLISH": "Ready to publish.",
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
            automation=app.config["W3D_AUTOMATION_ENABLED"],
        )

    @app.route("/api/products")
    def api_products():
        return jsonify([r.to_dict() for r in store.all()])

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
        app.config["W3D_AUTOMATION_ENABLED"] = not app.config["W3D_AUTOMATION_ENABLED"]
        return redirect(url_for("index"))

    # -- Settings (no YAML/code editing) -----------------------------------
    env_path = DEFAULT_CONFIG.parent / ".env"

    @app.route("/settings")
    def settings():
        secret_status = {k: secrets_env.is_set(k) for k in secrets_env.KNOWN_SECRETS}
        return render_template("settings.html", c=config, secret_status=secret_status, saved=request.args.get("saved"))

    @app.route("/settings", methods=["POST"])
    def save_settings():
        f = request.form

        def _bool(name): return f.get(name) in ("on", "true", "1", "yes")

        # Paths + modes + trigger.
        config.set("paths.ready_folder", f.get("ready_folder", "").strip())
        config.set("paths.work_folder", f.get("work_folder", "").strip() or "work")
        config.set("modes.dry_run", _bool("dry_run"))
        config.set("modes.auto_publish", _bool("auto_publish"))
        try:
            config.set("trigger.stability_delay_seconds", int(f.get("stability_delay_seconds", "60")))
        except ValueError:
            pass

        # Stores.
        config.set("stores.cults3d.enabled", _bool("cults3d_enabled"))
        config.set("stores.cults3d.asset_host", f.get("cults3d_asset_host", "google_drive"))
        config.set("stores.cults3d.license_code", f.get("cults3d_license_code", "").strip())
        config.set("stores.thangs.enabled", _bool("thangs_enabled"))
        config.set("stores.thangs.sync_folder", f.get("thangs_sync_folder", "").strip())
        config.set("stores.creality_cloud_eu.enabled", _bool("creality_eu_enabled"))
        config.set("stores.creality_cloud_eu.staging_folder", f.get("creality_eu_staging_folder", "").strip())
        config.set("stores.creality_cloud_cn.enabled", _bool("creality_cn_enabled"))
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
