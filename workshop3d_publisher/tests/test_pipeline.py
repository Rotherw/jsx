"""End-to-end pipeline: DRY_RUN, duplicate protection, resume, originals
untouched, format-update, per-platform failure isolation (spec 23)."""
from pathlib import Path

from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.models import State


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


def test_report_files_written(product_folder, config, tmp_path):
    folder = product_folder()
    pipe, _ = _pipeline(config, tmp_path)
    rec = pipe.on_folder_ready(folder)
    reports = Path(rec.package_path) / "reports"
    assert (reports / "publication_report.json").exists()
    assert (reports / "publication_report.md").exists()
