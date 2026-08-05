"""Thangs sync-mode staging tests (no real uploads)."""
import csv
from pathlib import Path

from workshop3d.config import Config
from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.models import State


def _config(tmp_path, dry_run, sync_folder=""):
    return Config({
        "paths": {"ready_folder": str(tmp_path / "ready"), "work_folder": str(tmp_path / "work")},
        "modes": {"dry_run": dry_run, "auto_publish": not dry_run, "require_approval": False},
        "trigger": {"stability_delay_seconds": 0, "stability_checks": 1,
                    "seconds_between_checks": 0, "ignore_patterns": []},
        "retry": {"max_attempts": 1, "backoff_seconds": [0]},
        "brand": {"name": "WorkShop3D", "signature": "Regards.\nRafal z WorkShop3D", "collections": []},
        "pricing": {"currency": "USD", "single_model": 4.99, "bundle_small": 13.99, "free_products": False},
        "licensing": {"default": {"owner": "WorkShop3D", "summary": "No redistribution."}},
        "categories": {"default": "terrain", "keyword_map": {"door": "terrain"}},
        "stores": {"thangs": {"enabled": True, "mode": "sync", "sync_folder": sync_folder}},
        "social": {},
        "links": {"main_link_priority": ["thangs"]},
    })


def test_thangs_dry_run(product_folder, tmp_path):
    config = _config(tmp_path, dry_run=True)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["thangs"]["status"] == "DRY_RUN"


def test_thangs_sync_without_folder_not_connected(product_folder, tmp_path):
    config = _config(tmp_path, dry_run=False, sync_folder="")
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["thangs"]["status"] == "NOT_CONNECTED"


def test_thangs_sync_stages_files_and_csv(product_folder, tmp_path):
    sync = tmp_path / "ThangsSync"
    config = _config(tmp_path, dry_run=False, sync_folder=str(sync))
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder(name="Dark Fantasy Dungeon Door"))

    assert rec.stores["thangs"]["status"] == "STAGED"
    # A per-model subfolder with the product files exists in the sync folder.
    model_dirs = [p for p in sync.iterdir() if p.is_dir()]
    assert len(model_dirs) == 1
    staged = list(model_dirs[0].glob("*"))
    assert any(p.suffix == ".stl" for p in staged)
    assert any(p.suffix == ".png" for p in staged)

    # CSV written with the exact Thangs columns and colon-separated tags.
    csv_path = sync / "thangs_bulk_upload.csv"
    assert csv_path.exists()
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == ["ModelName", "Description", "Tags", "Category", "SecondaryCategory"]
    assert ":" in rows[0]["Tags"]
    assert rows[0]["Category"] == "terrain"

    # Whole product is COMPLETED_WITH_WARNINGS and asks the user to run Sync.
    assert rec.state == State.COMPLETED_WITH_WARNINGS.value
    assert "Thangs Sync" in (rec.required_user_action or "")


def test_thangs_sync_idempotent_csv(product_folder, tmp_path):
    sync = tmp_path / "ThangsSync"
    config = _config(tmp_path, dry_run=False, sync_folder=str(sync))
    store = StateStore(tmp_path / "work" / "state.json")
    folder = product_folder(name="Barrel Prop")
    pipe = Pipeline(config, store)
    pipe.on_folder_ready(folder)
    pipe.run(store.find_by_folder("Barrel Prop"))  # re-run

    with open(sync / "thangs_bulk_upload.csv", newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("ModelName")]
    assert len(rows) == 1  # no duplicate row after re-run
