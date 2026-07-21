"""Entry point: starts the folder watcher and the local dashboard.

Usage:
    python -m workshop3d                 # watcher + dashboard
    python -m workshop3d --scan-once     # process current folders and exit
    python -m workshop3d --dashboard-only
"""
from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path

from .config import Config
from .state_store import StateStore
from .pipeline import Pipeline
from .folder_watcher import Watcher, scan_ready_folder, is_stable, has_pending_temp_files
from . import adapters  # noqa: F401  (registers adapters)


def build(config_path: str | None = None):
    config = Config.load(config_path)
    state_path = config.work_folder / "state.json"
    store = StateStore(state_path)
    pipeline = Pipeline(config, store)
    return config, store, pipeline


def scan_once(config: Config, pipeline: Pipeline) -> None:
    """Process every folder currently present (used for manual / test runs)."""
    ignore = config.get("trigger.ignore_patterns", []) or []
    for folder in scan_ready_folder(config):
        if has_pending_temp_files(folder, ignore):
            print(f"[scan] skipping {folder.name}: temp files present")
            continue
        print(f"[scan] processing {folder.name}")
        record = pipeline.on_folder_ready(folder)
        print(f"[scan]   -> {record.state}  {record.main_link or ''}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="workshop3d")
    parser.add_argument("--config", default=None)
    parser.add_argument("--scan-once", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    config, store, pipeline = build(args.config)
    print(f"[start] mode: {'DRY_RUN' if config.dry_run else 'AUTO_PUBLISH'}  "
          f"ready='{config.ready_folder}'  work='{config.work_folder}'")

    if args.scan_once:
        scan_once(config, pipeline)
        return

    from .dashboard.app import create_app
    app = create_app(config, store)

    if not args.dashboard_only:
        watcher = Watcher(config, on_ready=lambda folder: pipeline.on_folder_ready(folder))
        t = threading.Thread(target=watcher.run_forever, daemon=True)
        t.start()
        print("[start] folder watcher running")

    url = f"http://127.0.0.1:{args.port}/"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"[start] dashboard at {url}")
    app.run(port=args.port, debug=False)


if __name__ == "__main__":
    main()
