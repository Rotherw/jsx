"""Creality Cloud batch-staging tests (no real uploads)."""
from pathlib import Path

from workshop3d.config import Config
from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.models import State


def _config(tmp_path, dry_run, staging_folder="", mode="batch", browser_profile_set=False):
    store_cfg = {"enabled": True, "mode": mode, "staging_folder": staging_folder}
    return Config({
        "paths": {"ready_folder": str(tmp_path / "ready"), "work_folder": str(tmp_path / "work")},
        "modes": {"dry_run": dry_run, "auto_publish": not dry_run},
        "trigger": {"stability_delay_seconds": 0, "stability_checks": 1,
                    "seconds_between_checks": 0, "ignore_patterns": []},
        "retry": {"max_attempts": 1, "backoff_seconds": [0]},
        "brand": {"name": "WorkShop3D", "signature": "Regards.\nRafal z WorkShop3D", "collections": []},
        "pricing": {"currency": "USD", "single_model": 4.99, "bundle_small": 13.99, "free_products": False},
        "licensing": {"default": {"owner": "WorkShop3D", "summary": "No redistribution."}},
        "categories": {"default": "terrain", "keyword_map": {"door": "terrain"}},
        "stores": {"creality_cloud_eu": store_cfg},
        "social": {},
        "links": {"main_link_priority": ["creality_cloud_eu"]},
    })


def test_creality_dry_run(product_folder, tmp_path):
    config = _config(tmp_path, dry_run=True)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["creality_cloud_eu"]["status"] == "DRY_RUN"


def test_creality_batch_without_folder_not_connected(product_folder, tmp_path):
    config = _config(tmp_path, dry_run=False, staging_folder="")
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["creality_cloud_eu"]["status"] == "NOT_CONNECTED"


def test_creality_batch_stages_files_and_info(product_folder, tmp_path):
    staging = tmp_path / "CrealityEU"
    config = _config(tmp_path, dry_run=False, staging_folder=str(staging))
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder(name="Dark Fantasy Dungeon Door"))

    assert rec.stores["creality_cloud_eu"]["status"] == "STAGED"
    model_dirs = [p for p in staging.iterdir() if p.is_dir()]
    assert len(model_dirs) == 1
    staged = list(model_dirs[0].glob("*"))
    assert any(p.suffix == ".stl" for p in staged)
    info = model_dirs[0] / "creality_upload_info.txt"
    assert info.exists()
    text = info.read_text(encoding="utf-8")
    assert "Title:" in text and "Tags:" in text and "Description:" in text
    assert rec.state == State.COMPLETED_WITH_WARNINGS.value


def test_creality_browser_mode_needs_attention(product_folder, tmp_path, monkeypatch):
    monkeypatch.setenv("CREALITY_EU_BROWSER_PROFILE", "default")
    config = _config(tmp_path, dry_run=False, mode="browser")
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["creality_cloud_eu"]["status"] == "NEEDS_ATTENTION"
