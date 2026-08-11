"""End-to-end pipeline: DRY_RUN, duplicate protection, resume, originals
untouched, format-update, per-platform failure isolation (spec 23)."""
from pathlib import Path

from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.models import ProductRecord, State


def _pipeline(config, tmp_path):
    store = StateStore(tmp_path / "work" / "state.json")
    return Pipeline(config, store), store


def test_dry_run_completes_without_real_publish(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    assert rec.state in (State.COMPLETED.value, State.COMPLETED_WITH_WARNINGS.value)
    # Every store result is a simulation, never a real publish.
    for r in rec.stores.values():
        assert r["status"] == "DRY_RUN"
    assert rec.main_link  # dry-run preview link present
    assert rec.progress_step == rec.progress_total == 9
    assert rec.completed_at is not None


def test_dashboard_shows_live_progress_counts_and_finish_time(product_folder, config, tmp_path):
    pipe, store = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(product_folder(name="Progress Door"))

    from workshop3d.dashboard.app import create_app
    response = create_app(config, store).test_client().get("/")

    assert response.status_code == 200
    assert b"Etap 9/9" in response.data
    assert b"Sklepy: 2/2" in response.data
    assert "Zakończono".encode() in response.data
    assert rec.completed_at is not None


def test_dashboard_shows_useful_publication_statistics(product_folder, config, tmp_path):
    pipe, store = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(product_folder(name="Statistics Door"))
    rec.stores["cults3d"]["status"] = "PUBLISHED"
    rec.stores["thangs"]["status"] = "FAILED"
    store.upsert(rec)

    from workshop3d.dashboard.app import create_app
    response = create_app(config, store).test_client().get("/")

    assert response.status_code == 200
    assert b"50%" in response.data
    assert b"Cults3D" in response.data
    assert b"1/1 opublikowane" in response.data
    assert "gotowych dzisiaj".encode() in response.data
    assert "średni czas produktu".encode() in response.data


def test_completion_sends_clear_ready_notification(product_folder, config, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(
        "workshop3d.notification_service.notify",
        lambda title, message: messages.append((title, message)),
    )

    pipe, _ = _pipeline(config, tmp_path)
    pipe.on_folder_ready(product_folder(name="Notification Door"))

    assert len(messages) == 1
    title, message = messages[0]
    assert "GOTOWE" in title
    assert "2/2" in message
    assert "koniec" in message
    assert "panelu" in message


def test_cloud_enabled_completes_only_after_both_finished_folders_exist(
    product_folder, config, tmp_path, monkeypatch
):
    messages = []
    monkeypatch.setattr(
        "workshop3d.notification_service.notify",
        lambda title, message: messages.append((title, message)),
    )
    google = tmp_path / "google"
    broken_nextcloud = tmp_path / "nextcloud-file"
    broken_nextcloud.write_text("not a folder")
    config.set("cloud_sync.enabled", True)
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.local_folder", str(broken_nextcloud))
    folder = product_folder(name="Cloud Completion")
    pipe, _ = _pipeline(config, tmp_path)

    rec = pipe.on_folder_ready(folder)

    assert rec.state == State.AWAITING_CLOUD_SYNC.value
    assert rec.completed_at is None
    assert rec.progress_step == 8 and rec.progress_total == 9
    assert not any("GOTOWE" in title for title, _ in messages)
    assert (google / "Gotowe do sklepu" / folder.name).is_dir()

    nextcloud = tmp_path / "nextcloud"
    config.set("cloud_sync.nextcloud.local_folder", str(nextcloud))
    rec.cloud_sync["next_retry_at"] = 0
    rec = pipe.retry_cloud_sync(rec)

    assert rec.state in (State.COMPLETED.value, State.COMPLETED_WITH_WARNINGS.value)
    assert rec.cloud_sync["status"] == "SYNCED"
    assert rec.completed_at is not None
    assert not (google / "Gotowe do sklepu" / folder.name).exists()
    assert not (nextcloud / "Gotowe do sklepu" / folder.name).exists()
    assert (google / "Opublikowane" / folder.name).is_dir()
    assert (nextcloud / "Opublikowane" / folder.name).is_dir()
    assert rec.folder_path == str(google / "Opublikowane" / folder.name)
    assert rec.cloud_archive["status"] == "ARCHIVED"
    assert sum("GOTOWE" in title for title, _ in messages) == 1


def test_originals_are_untouched(product_folder, config, tmp_path):
    folder = product_folder()
    before = {p.name: p.stat().st_size for p in folder.iterdir()}
    pipe, _ = _pipeline(config, tmp_path)
    pipe.on_folder_ready(folder)
    after = {p.name: p.stat().st_size for p in folder.iterdir()}
    assert before == after  # no rename / delete / modify of source files


def test_missing_required_sets_waiting(product_folder, config, tmp_path):
    folder = product_folder(stl=False)
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    assert rec.state == State.WAITING_FOR_REQUIRED_FILES.value


def test_corrupt_image_stops_before_preparation(product_folder, config, tmp_path):
    folder = product_folder(name="Broken Preview")
    next(folder.glob("*.png")).write_bytes(b"this is not a png")
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    assert rec.state == State.NEEDS_ATTENTION.value
    assert rec.package_path is None
    assert rec.stores == {}


def test_live_auto_publish_off_prepares_but_never_calls_store(product_folder, config, tmp_path, monkeypatch):
    config.set("modes.dry_run", False)
    config.set("modes.auto_publish", False)
    config.set("modes.require_approval", False)

    from workshop3d.adapters.stores.cults3d import Cults3DAdapter
    called = []
    monkeypatch.setattr(Cults3DAdapter, "publish", lambda *args: called.append(True))

    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(product_folder(name="Manual Only"))
    assert rec.state == State.READY_TO_PUBLISH.value
    assert called == []
    assert rec.stores == {}


def test_duplicate_protection(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, store = _pipeline(config, tmp_path)
    rec1 = pipe.on_folder_ready(folder)
    n_after_first = len(store)
    # Re-run: same folder + same checksums -> same product id, no duplicate.
    rec2 = pipe.on_folder_ready(folder)
    assert rec1.product_id == rec2.product_id
    assert len(store) == n_after_first


def test_resume_after_restart(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    pid = rec.product_id

    # Simulate a fresh process: brand-new store from the same JSON file.
    store2 = StateStore(tmp_path / "work" / "state.json")
    loaded = store2.get(pid)
    assert loaded is not None
    assert loaded.state == rec.state
    assert loaded.folder_name == folder.name


def test_format_update_no_duplicate_listing(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, store = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    stores_before = dict(rec.stores)

    # Add a GLB later -> product identity changes (new checksum set), but the
    # same folder record is updated rather than duplicated.
    import struct
    (folder / "extra.glb").write_bytes(b"glTF" + struct.pack("<II", 2, 20) + b"\x00" * 12)
    rec2 = pipe.on_folder_ready(folder)
    assert rec2.folder_name == rec.folder_name
    assert set(rec2.stores.keys()) == set(stores_before.keys())
    assert "extra.glb" in rec2.glb_files


def test_platform_failure_isolation(product_folder, config, tmp_path, monkeypatch):
    folder = product_folder()
    pipe, _ = _pipeline(config, tmp_path)

    # Force the Cults3D adapter to raise; Thangs must still succeed.
    from workshop3d.adapters.stores.cults3d import Cults3DAdapter
    def boom(self, record, workspace):
        raise RuntimeError("simulated Cults3D outage")
    monkeypatch.setattr(Cults3DAdapter, "publish", boom)

    rec = pipe.on_folder_ready(folder)
    assert rec.stores["cults3d"]["status"] == "FAILED"
    assert rec.stores["thangs"]["status"] == "DRY_RUN"
    assert rec.state == State.COMPLETED_WITH_WARNINGS.value


def test_social_only_after_store_success(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    # Facebook enabled + a live (dry-run) listing exists -> a post was prepared.
    assert "facebook" in rec.social
    assert rec.social["facebook"]["status"] == "DRY_RUN"


def test_social_waits_until_every_browser_store_job_finishes(config, tmp_path, monkeypatch):
    pipe, _ = _pipeline(config, tmp_path)
    rec = ProductRecord("queued", "Queued Product", str(tmp_path / "queued"))
    rec.state = State.PUBLISHED.value
    rec.stores = {
        "cults3d": {
            "status": "PUBLISHED",
            "url": "https://cults3d.com/en/3d-model/game/queued-product",
        },
        "thangs": {"status": "BROWSER_QUEUED"},
    }
    calls = []
    monkeypatch.setattr(
        "workshop3d.publication_manager.promote_social",
        lambda *args: calls.append(args),
    )

    pipe._promote(rec)
    assert calls == []

    rec.stores["thangs"]["status"] = "FAILED"
    pipe._promote(rec)
    assert len(calls) == 1


def test_report_files_written(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    reports = Path(rec.package_path) / "reports"
    assert (reports / "publication_report.json").exists()
    assert (reports / "publication_report.md").exists()


def test_render_graphics_disabled_uses_original_pngs(product_folder, config, tmp_path):
    # User brands images with an external tool -> PNGs must pass through as-is.
    config._data["brand"]["render_graphics"] = False
    folder = product_folder(name="Unbranded Door")
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    media = [m for m in rec.media if m.endswith(".png")]
    assert media, "cover copy expected"
    # The copied cover must be byte-identical to the delivered PNG (no captions).
    src = next(folder.glob("*.png")).read_bytes()
    assert Path(media[0]).read_bytes() == src


def test_extra_tool_files_never_reach_the_sales_package(product_folder, config, tmp_path):
    # Preparation tools (e.g. the F: brander) drop RAPORT.html etc. into the
    # product folder. Those must be archived but never shipped in the ZIP.
    folder = product_folder(name="Prepared By Tool")
    (folder / "RAPORT.html").write_text("<html>raport</html>", encoding="utf-8")
    (folder / "notatki.txt").write_text("notes", encoding="utf-8")
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)

    base = Path(rec.package_path)
    files = {p.name for p in (base / "files").iterdir()}
    assert "RAPORT.html" not in files and "notatki.txt" not in files
    # Archived verbatim in source/.
    assert (base / "source" / "RAPORT.html").exists()
    # And absent from the customer ZIP (which legitimately has README/LICENSE).
    import zipfile
    zip_path = next((base / "package").glob("*.zip"))
    names = {n.rsplit("/", 1)[-1] for n in zipfile.ZipFile(zip_path).namelist()}
    assert "RAPORT.html" not in names and "notatki.txt" not in names


def test_nested_duplicate_basenames_are_preserved_and_packaged_uniquely(product_folder, config, tmp_path):
    from conftest import make_binary_stl, make_png

    folder = product_folder(name="Nested Parts", png=False, stl=False)
    for sub in ("left", "right"):
        target = folder / sub
        target.mkdir()
        make_png(target / "preview.png")
        make_binary_stl(target / "part.stl")

    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    assert rec.state in (State.COMPLETED.value, State.COMPLETED_WITH_WARNINGS.value)
    assert set(rec.stl_files) == {"left/part.stl", "right/part.stl"}
    assert set(rec.png_files) == {"left/preview.png", "right/preview.png"}
    base = Path(rec.package_path)
    assert (base / "source" / "left" / "part.stl").exists()
    assert (base / "source" / "right" / "part.stl").exists()
    assert len(list((base / "files").glob("*.stl"))) == 2
