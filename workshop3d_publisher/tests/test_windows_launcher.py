"""Regression checks for the one-click Windows launcher and shortcuts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_launcher_ignores_obsolete_app_py_shortcut_argument():
    launcher = (ROOT / "run.bat").read_text(encoding="utf-8")
    assert 'if /I "%~x1"==".py"' in launcher
    assert 'call ".venv\\Scripts\\python.exe" -m workshop3d' in launcher
    assert "Always check" in launcher
    assert 'if /I not "%~1"=="--no-browser"' in launcher
    assert "exit /b 0" in launcher
    assert "open_in_chrome" in launcher


def test_installers_clear_desktop_arguments_and_keep_hidden_autostart():
    installer = (ROOT / "install.bat").read_text(encoding="utf-8")
    assert "$s.Arguments='';" in installer
    assert "run_hidden.vbs" in installer

    bootstrap = (REPO / "1_ZAINSTALUJ.bat").read_text(encoding="utf-8")
    assert "WorkShop3D Publisher.lnk" in bootstrap
    assert "call install.bat" in bootstrap
    assert '/XF "config.yaml" ".env"' in bootstrap


def test_installers_connect_nextcloud_directly_without_full_desktop_copy():
    installer = (ROOT / "install.bat").read_text(encoding="utf-8")
    # Installation must never wait in a console for the Login Flow.  The
    # running background app connects and performs the initial mirror.
    assert "--connect-nextcloud" not in installer
    assert "pierwsza kopia Google - Nextcloud rusza automatycznie w tle" in installer
    assert "--prepare-browser" in installer
    assert "Nextcloud.NextcloudDesktop" not in installer
    assert "run_hidden.vbs" in installer
    assert "http://127.0.0.1:5000/" in installer
    assert "open_in_chrome" in installer


def test_update_restores_automation_and_chrome_pairing():
    updater = (ROOT / "update.bat").read_text(encoding="utf-8")
    # /MIR over browser_extension replaces the locally generated bootstrap.js
    # with the empty placeholder from the repository, and an older config.yaml
    # is deliberately preserved -- both have to be repaired, or the update
    # succeeds while nothing can ever be published again.
    assert 'robocopy "%SRC%\\browser_extension" "browser_extension" /MIR' in updater
    assert "--configure-zero-touch" in updater
    assert "--prepare-browser" in updater


def test_startup_rewrites_the_pairing_file_after_an_update(tmp_path, monkeypatch):
    """A mirrored placeholder bootstrap.js must heal on the next start."""
    from workshop3d import __main__ as entry
    from workshop3d.browser_bridge import BrowserBridge
    from workshop3d.config import Config

    config = Config({"paths": {"work_folder": str(tmp_path / "work")},
                     "browser": {"server_url": "http://127.0.0.1:5000"}})
    target = ROOT / "browser_extension" / "bootstrap.js"
    original = target.read_text(encoding="utf-8")
    try:
        target.write_text('globalThis.WORKSHOP3D_BOOTSTRAP = {"pairingKey": ""};\n',
                          encoding="utf-8")
        written = entry.prepare_browser_extension(config)
        assert written == target
        content = target.read_text(encoding="utf-8")
        assert BrowserBridge.shared(config).pairing_key in content
        assert '"pairingKey": ""' not in content
    finally:
        target.write_text(original, encoding="utf-8")


def test_extension_pairs_itself_and_handles_creality_two_step_form():
    worker = (ROOT / "browser_extension" / "service_worker.js").read_text(encoding="utf-8")
    options = (ROOT / "browser_extension" / "options.html").read_text(encoding="utf-8")
    manifest = (ROOT / "browser_extension" / "manifest.json").read_text(encoding="utf-8")
    assert 'importScripts("bootstrap.js")' in worker
    assert "discoveredStores" in worker
    assert '"stl/cad"' in worker
    assert "Creality is a two-step form" in worker
    assert "fillSocialComposer" in worker
    assert "authorizeNextcloudTabs" in worker
    assert "LOGIN_REQUIRED" in worker
    assert "https://cloud.workshop3d.pl/*" in manifest
    assert "Kod parowania" not in options
