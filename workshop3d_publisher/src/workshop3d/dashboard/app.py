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

from ..config import Config
from ..state_store import StateStore
from ..pipeline import Pipeline


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
