"""Entry point: starts the folder watcher and the local dashboard.

Usage:
    python -m workshop3d                 # watcher + dashboard
    python -m workshop3d --scan-once     # process current folders and exit
    python -m workshop3d --dashboard-only
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

import shutil

from .config import Config, DEFAULT_CONFIG, EXAMPLE_CONFIG
from .state_store import StateStore
from .pipeline import Pipeline
from .folder_watcher import Watcher, scan_ready_folder, is_stable, has_pending_temp_files
from . import adapters, secrets_env  # noqa: F401  (adapters registers adapters)
from .automation import AutomationControl
from .browser_bridge import BrowserBridge
from .browser_open import open_in_chrome
from . import cloud_inbox, cloud_mirror, cloud_sync, nextcloud_api


def prepare_browser_extension(config: Config) -> Path:
    """Write the local bridge details into the bundled Chrome extension.

    The file stays on this PC and replaces the former copy/paste pairing form.
    It contains no website password, cookie or Google/Nextcloud credential.
    """
    bridge = BrowserBridge.shared(config)
    extension_dir = Path(__file__).resolve().parents[2] / "browser_extension"
    target = extension_dir / "bootstrap.js"
    payload = {
        "serverUrl": str(config.get("browser.server_url", "http://127.0.0.1:5000")),
        "pairingKey": bridge.pairing_key,
    }
    target.write_text(
        "// Generated locally by WorkShop3D Publisher.\n"
        f"globalThis.WORKSHOP3D_BOOTSTRAP = Object.freeze({json.dumps(payload)});\n",
        encoding="utf-8",
    )
    return target


def build(config_path: str | None = None):
    # First run: create a real config.yaml from the example so the user never
    # has to touch a file -- everything else is set in the dashboard Settings.
    if config_path is None and not DEFAULT_CONFIG.exists() and EXAMPLE_CONFIG.exists():
        shutil.copy2(EXAMPLE_CONFIG, DEFAULT_CONFIG)
        print(f"[start] created {DEFAULT_CONFIG.name} (full automation enabled)")

    config = Config.load(config_path)
    # Load locally-stored API keys/tokens into the environment.
    secrets_env.load_env(DEFAULT_CONFIG.parent / ".env")

    # Make sure the drop folder exists so the user can start immediately.
    try:
        config.ready_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[start] cannot create ready folder '{config.ready_folder}': {exc}")

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


def _retry_clouds_forever(config: Config, store: StateStore, pipeline: Pipeline) -> None:
    """Finish cloud-waiting products without publishing their stores twice."""
    while True:  # pragma: no cover - production background loop
        try:
            for record in store.all():
                if (
                    cloud_sync.should_retry(record.cloud_sync)
                    or cloud_sync.should_retry(record.cloud_archive)
                ):
                    pipeline.retry_cloud_sync(record)
        except Exception as exc:
            print(f"[cloud-retry] error: {exc}")
        time.sleep(10)


def _connect_nextcloud_and_sync_once(config: Config) -> bool:
    """Ensure direct WebDAV credentials exist, then mirror immediately."""
    existing = nextcloud_api.NextcloudWebDAV.from_config(config)
    if existing is not None:
        try:
            if existing.validate():
                cloud_mirror.sync_once(config)
                return True
        except nextcloud_api.NextcloudError:
            pass
    try:
        nextcloud_api.connect_login_flow(config, timeout=3 * 60)
    except nextcloud_api.NextcloudError as exc:
        print(f"[nextcloud] automatic connection: {exc}")
        return False
    result = cloud_mirror.sync_once(config)
    print(f"[nextcloud] {result.get('message', 'initial mirror finished')}")
    return result.get("status") == "SYNCED"


def _connect_nextcloud_forever(config: Config) -> None:
    """Retry in the background until the requested cloud mirror is live."""
    while not _connect_nextcloud_and_sync_once(config):  # pragma: no cover - Windows loop
        time.sleep(120)


def main() -> None:
    parser = argparse.ArgumentParser(prog="workshop3d")
    parser.add_argument("--config", default=None)
    parser.add_argument("--scan-once", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--configure-zero-touch", action="store_true")
    parser.add_argument("--prepare-browser", action="store_true")
    parser.add_argument("--connect-nextcloud", action="store_true")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    config, store, pipeline = build(args.config)
    if args.connect_nextcloud:
        local = cloud_sync.discover_nextcloud_folder(config)
        if local is not None:
            print(f"[setup] Nextcloud Desktop already connected: {local}")
            return
        existing = nextcloud_api.NextcloudWebDAV.from_config(config)
        if existing is not None:
            try:
                if existing.validate():
                    print("[setup] Nextcloud already connected directly")
                    return
            except nextcloud_api.NextcloudError:
                pass
        print("[setup] opening official Nextcloud authorization in the browser")
        print("[setup] approve access once; the account password is not copied")
        try:
            nextcloud_api.connect_login_flow(config, timeout=5 * 60)
        except nextcloud_api.NextcloudError as exc:
            print(f"[setup] Nextcloud not connected: {exc}")
            raise SystemExit(1) from exc
        print("[setup] Nextcloud connected")
        return
    if args.configure_zero_touch:
        config.set("modes.zero_touch", True)
        config.set("modes.dry_run", False)
        config.set("modes.auto_publish", True)
        config.set("modes.require_approval", False)
        config.set("browser.auto_submit", True)
        config.set("cloud_sync.enabled", True)
        config.set("cloud_sync.mirror_enabled", True)
        config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
        config.set("cloud_sync.published_folder", "Opublikowane")
        # No Google Drive for desktop: mirroring the whole model library locally
        # cripples the machine. The working area is the local drop folder.
        config.set("cloud_sync.google_drive.enabled", False)
        config.set("cloud_sync.google_drive.folder_name", "Folder Sync")
        config.set(
            "cloud_sync.google_drive.folder_id",
            "1bKkH3_P2XYCtFtSv4HlzmWE16cqjYGlo",
        )
        config.set("cloud_sync.nextcloud.server_url", "https://cloud.workshop3d.pl")
        config.set("cloud_sync.nextcloud.folder_path", "Folder Sync")
        config.set("cloud_sync.nextcloud.prefer_webdav", True)
        config.set("cloud_sync.nextcloud.auto_connect", True)
        config.set("cloud_sync.nextcloud.local_folder", "")
        config.set("cloud_sync.mirror_interval_seconds", 15)
        config.set("cloud_sync.process_existing_inbox", True)
        for store in (
            "cults3d",
            "thangs",
            "creality_cloud_eu",
            "creality_cloud_cn",
        ):
            config.set(f"stores.{store}.enabled", True)
            config.set(f"stores.{store}.mode", "browser")
            config.set(f"stores.{store}.publish_as", "public")
        for network in (
            "facebook",
            "instagram",
            "x",
            "pinterest",
            "bluesky",
            "mastodon",
            "tiktok",
            "youtube",
        ):
            config.set(f"social.{network}.enabled", True)
            config.set(f"social.{network}.mode", "browser")
        if config.get("asset_hosts.google_drive.root_folder_name") in (None, "", "FolderSync"):
            config.set(
                "asset_hosts.google_drive.root_folder_name",
                "WorkShop3D Public Assets",
            )
        config.save()
        print("[setup] full automation enabled: daily use only requires dropping a folder")
        return
    if args.prepare_browser:
        target = prepare_browser_extension(config)
        print(f"[setup] Chrome connection prepared automatically: {target}")
        return
    print(f"[start] mode: {'DRY_RUN' if config.dry_run else 'AUTO_PUBLISH'}  "
          f"ready='{config.ready_folder}'  work='{config.work_folder}'")

    if args.scan_once:
        scan_once(config, pipeline)
        return

    resumed = pipeline.resume_zero_touch_pending()
    if resumed:
        print(f"[start] resumed {len(resumed)} product(s) without approval")

    from .dashboard.app import create_app
    automation = AutomationControl(enabled=True)
    bridge = BrowserBridge.shared(config)
    app = create_app(
        config,
        store,
        automation=automation,
        bridge=bridge,
        dashboard_port=args.port,
    )

    if not args.dashboard_only:
        if cloud_sync.enabled(config):
            if config.get("cloud_sync.nextcloud.auto_connect", True):
                connect_thread = threading.Thread(
                    target=_connect_nextcloud_forever,
                    args=(config,),
                    daemon=True,
                )
                connect_thread.start()

            # Without Google Drive for desktop there is no second inbox to
            # watch: the local drop folder below is the working area, so the
            # extra watcher would only report "waiting" forever.
            if cloud_sync.working_provider(config) == "google_drive":
                google_inbox = cloud_inbox.CloudInboxWatcher(
                    config,
                    on_ready=lambda folder: pipeline.on_folder_ready(folder),
                    enabled=lambda: automation.enabled,
                )
                inbox_thread = threading.Thread(
                    target=google_inbox.run_forever, daemon=True
                )
                inbox_thread.start()
                print("[start] Google FolderSync/Gotowe do sklepu watcher running")

            retry_thread = threading.Thread(
                target=_retry_clouds_forever,
                args=(config, store, pipeline),
                daemon=True,
            )
            retry_thread.start()

            if config.get("cloud_sync.mirror_enabled", True):
                mirror_thread = threading.Thread(
                    target=cloud_mirror.run_forever,
                    args=(config,),
                    daemon=True,
                )
                mirror_thread.start()
                print(
                    "[start] finished-folder push to the Nextcloud archive running "
                    f"(working area: {cloud_sync.working_root(config)})"
                )

        watcher = Watcher(
            config,
            on_ready=lambda folder: pipeline.on_folder_ready(folder),
            enabled=lambda: automation.enabled,
        )
        t = threading.Thread(target=watcher.run_forever, daemon=True)
        t.start()
        print("[start] folder watcher running")

    url = f"http://127.0.0.1:{args.port}/"
    if not args.no_browser:
        threading.Timer(1.0, lambda: open_in_chrome(url)).start()
    print(f"[start] dashboard at {url}")
    app.run(port=args.port, debug=False)


if __name__ == "__main__":
    main()
