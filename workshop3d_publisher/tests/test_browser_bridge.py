"""Authenticated Chrome bridge and honest publication-state tests."""
from pathlib import Path

from workshop3d.browser_bridge import BrowserBridge
from workshop3d.dashboard.app import create_app
from workshop3d.models import ProductRecord, State
from workshop3d.state_store import StateStore


def _workspace(tmp_path: Path) -> Path:
    base = tmp_path / "work" / "product"
    (base / "files").mkdir(parents=True)
    (base / "media").mkdir()
    (base / "files" / "model.stl").write_bytes(b"solid model")
    (base / "media" / "cover.png").write_bytes(b"png")
    return base


def _record(tmp_path: Path) -> ProductRecord:
    return ProductRecord(
        product_id="prod-1",
        folder_name="Dungeon Door",
        folder_path=str(tmp_path / "ready" / "Dungeon Door"),
        state=State.PUBLISHING.value,
        metadata={
            "TITLE": "Dungeon Door",
            "DESCRIPTION_EN": "A printable door.",
            "SHORT_DESCRIPTION": "Printable door",
            "TAGS": ["door", "terrain"],
            "CATEGORY": "terrain",
            "PRICE": {"amount": 4.99, "currency": "USD"},
            "MADE_WITH_AI": False,
        },
    )


def test_bridge_claim_hides_local_paths_and_validates_success(config, tmp_path):
    config.set("paths.work_folder", str(tmp_path / "runtime"))
    bridge = BrowserBridge(config, tmp_path / "bridge.json")
    record = _record(tmp_path)
    job = bridge.queue_store_job("cults3d", record, str(_workspace(tmp_path)), {})

    public = bridge.claim_next("http://127.0.0.1:5000")
    assert public["id"] == job["id"]
    assert "path" not in public["files"][0]
    assert public["files"][0]["url"].startswith("http://127.0.0.1:5000/")

    invalid = bridge.record_result(job["id"], {
        "status": "PUBLISHED",
        "url": "https://evil.example/fake",
    })
    assert invalid["status"] == "NEEDS_ATTENTION"


def test_dashboard_bridge_requires_pairing_key_and_updates_record(config, tmp_path):
    config.set("paths.work_folder", str(tmp_path / "runtime"))
    bridge = BrowserBridge(config, tmp_path / "bridge.json")
    record = _record(tmp_path)
    job = bridge.queue_store_job("cults3d", record, str(_workspace(tmp_path)), {})
    record.stores["cults3d"] = bridge.as_store_result(job).__dict__

    store = StateStore(tmp_path / "state.json")
    store.upsert(record)
    app = create_app(config, store, bridge=bridge)
    client = app.test_client()

    assert client.get("/api/browser/jobs/next").status_code == 401
    headers = {"X-WorkShop3D-Key": bridge.pairing_key}
    assert client.post("/api/browser/heartbeat", json={"version": "0.2.0"}, headers=headers).status_code == 200
    claimed = client.get("/api/browser/jobs/next", headers=headers)
    assert claimed.status_code == 200

    result = client.post(
        f"/api/browser/jobs/{job['id']}/result",
        json={
            "status": "PUBLISHED",
            "url": "https://cults3d.com/en/3d-model/game/dungeon-door",
            "message": "done",
        },
        headers=headers,
    )
    assert result.status_code == 200
    updated = store.get("prod-1")
    assert updated.stores["cults3d"]["status"] == "PUBLISHED"
    assert updated.state in (State.COMPLETED.value, State.COMPLETED_WITH_WARNINGS.value)


def test_file_download_uses_separate_job_token(config, tmp_path):
    config.set("paths.work_folder", str(tmp_path / "runtime"))
    bridge = BrowserBridge(config, tmp_path / "bridge.json")
    job = bridge.queue_store_job("thangs", _record(tmp_path), str(_workspace(tmp_path)), {})
    store = StateStore(tmp_path / "state.json")
    app = create_app(config, store, bridge=bridge)
    client = app.test_client()

    assert client.get(f"/api/browser/jobs/{job['id']}/files/0?token=wrong").status_code == 404
    response = client.get(
        f"/api/browser/jobs/{job['id']}/files/0?token={job['file_token']}"
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Access-Control-Allow-Private-Network"] == "true"

    preflight = client.options(
        f"/api/browser/jobs/{job['id']}/files/0?token={job['file_token']}"
    )
    assert preflight.status_code == 200
    assert preflight.headers["Access-Control-Allow-Methods"] == "GET, OPTIONS"
