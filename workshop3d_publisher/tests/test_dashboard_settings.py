"""Dashboard Settings page: save config + secrets without editing files by hand."""
import os

from workshop3d.config import Config
from workshop3d.state_store import StateStore
from workshop3d.dashboard.app import create_app
from workshop3d import secrets_env


def _app(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "paths: {ready_folder: r, work_folder: w}\n"
        "modes: {dry_run: true, auto_publish: false}\n"
        "stores: {cults3d: {enabled: true}, thangs: {enabled: false}}\n",
        encoding="utf-8",
    )
    config = Config.load(cfg_file)
    store = StateStore(tmp_path / "state.json")
    return create_app(config, store), config


def test_settings_page_renders(tmp_path):
    app, _ = _app(tmp_path)
    r = app.test_client().get("/settings")
    assert r.status_code == 200
    assert b"Ustawienia" in r.data


def test_saving_settings_updates_config_live(tmp_path, monkeypatch):
    # config.save() writes to the package DEFAULT_CONFIG; redirect it to tmp.
    import workshop3d.config as cfgmod
    monkeypatch.setattr(cfgmod, "DEFAULT_CONFIG", tmp_path / "config.yaml")
    import workshop3d.dashboard.app as appmod
    monkeypatch.setattr(appmod, "DEFAULT_CONFIG", tmp_path / "config.yaml")

    app, config = _app(tmp_path)
    client = app.test_client()
    r = client.post("/settings", data={
        "ready_folder": "C:/W3D/Ready",
        "work_folder": "C:/W3D/work",
        "auto_publish": "on",              # dry_run unchecked -> false
        "stability_delay_seconds": "30",
        "thangs_enabled": "on",
        "thangs_sync_folder": "C:/W3D/ThangsSync",
        "secret_CULTS3D_API_KEY": "supersecret",
    }, follow_redirects=False)
    assert r.status_code in (301, 302)

    # Live, in-memory config reflects the change immediately.
    assert config.get("paths.ready_folder") == "C:/W3D/Ready"
    assert config.dry_run is False
    assert config.auto_publish is True
    assert config.get("stores.thangs.sync_folder") == "C:/W3D/ThangsSync"
    # Secret went to a local .env and into the environment, not the repo.
    env_file = tmp_path / ".env"
    assert env_file.exists()
    assert "supersecret" in env_file.read_text()
    assert os.environ.get("CULTS3D_API_KEY") == "supersecret"
    # Cleanup env.
    os.environ.pop("CULTS3D_API_KEY", None)


def test_cross_site_page_cannot_change_local_settings(tmp_path):
    app, config = _app(tmp_path)
    client = app.test_client()
    response = client.post(
        "/settings",
        data={"auto_publish": "on"},
        headers={"Origin": "https://malicious.example"},
    )
    assert response.status_code == 403
    assert config.auto_publish is False
