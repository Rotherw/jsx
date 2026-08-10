"""Approval gate + preview page: user sees content before anything is sent."""
from workshop3d.config import Config
from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.dashboard.app import create_app
from workshop3d.models import State


def _config(tmp_path, require_approval=True, dry_run=False):
    return Config({
        "paths": {"ready_folder": str(tmp_path / "ready"), "work_folder": str(tmp_path / "work")},
        "modes": {"dry_run": dry_run, "auto_publish": True, "require_approval": require_approval},
        "trigger": {"stability_delay_seconds": 0, "stability_checks": 1,
                    "seconds_between_checks": 0, "ignore_patterns": []},
        "retry": {"max_attempts": 1, "backoff_seconds": [0]},
        "brand": {"name": "WorkShop3D", "signature": "Regards.\nRafal z WorkShop3D", "collections": []},
        "pricing": {"currency": "USD", "single_model": 4.99, "bundle_small": 13.99, "free_products": False},
        "licensing": {"default": {"owner": "WorkShop3D", "summary": "No redistribution."}},
        "categories": {"default": "terrain", "keyword_map": {"door": "terrain"}},
        "stores": {"thangs": {"enabled": True, "mode": "sync", "sync_folder": str(tmp_path / "ThangsSync")}},
        "social": {"store_handles": {"thangs": "@thangs3d"}, "mastodon": {"enabled": True}},
        "links": {"main_link_priority": ["thangs"]},
    })


def test_stops_at_awaiting_approval_before_sending(product_folder, tmp_path):
    config = _config(tmp_path, require_approval=True, dry_run=False)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    # Prepared but NOT sent: no store result yet, waiting for the user.
    assert rec.state == State.AWAITING_APPROVAL.value
    assert not rec.stores
    assert rec.metadata.get("TITLE")           # content is ready to preview


def test_preview_page_shows_listing_and_posts(product_folder, tmp_path):
    config = _config(tmp_path, require_approval=True, dry_run=False)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder(name="Dark Fantasy Dungeon Door"))
    app = create_app(config, store)
    r = app.test_client().get(f"/product/{rec.product_id}")
    assert r.status_code == 200
    assert b"Dark Fantasy Dungeon Door" in r.data
    assert b"Zatwierdz i publikuj" in r.data          # approval button present
    assert b"mastodon" in r.data                        # post preview present
    assert "@thangs3d".encode() in r.data               # store tag shown in preview


def test_approve_publishes(product_folder, tmp_path):
    config = _config(tmp_path, require_approval=True, dry_run=False)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    app = create_app(config, store)
    resp = app.test_client().post(f"/publish/{rec.product_id}")
    assert resp.status_code in (301, 302)
    after = store.get(rec.product_id)
    assert after.state in (State.COMPLETED.value, State.COMPLETED_WITH_WARNINGS.value)
    assert "thangs" in after.stores                    # actually published after approval


def test_no_gate_when_disabled(product_folder, tmp_path):
    config = _config(tmp_path, require_approval=False, dry_run=False)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.state != State.AWAITING_APPROVAL.value
    assert rec.stores                                   # published straight away
