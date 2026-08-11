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
    installers = [
        (ROOT / "install.bat").read_text(encoding="utf-8"),
        (REPO / "1_ZAINSTALUJ.bat").read_text(encoding="utf-8"),
    ]
    for installer in installers:
        assert "$s.Arguments='';" in installer
        assert "run_hidden.vbs" in installer


def test_installers_connect_nextcloud_directly_without_full_desktop_copy():
    installers = [
        (ROOT / "install.bat").read_text(encoding="utf-8"),
        (REPO / "1_ZAINSTALUJ.bat").read_text(encoding="utf-8"),
    ]
    for installer in installers:
        assert "--connect-nextcloud" in installer
        assert "Nextcloud.NextcloudDesktop" not in installer
        assert "run_hidden.vbs" in installer
        assert "http://127.0.0.1:5000/" in installer
        assert "open_in_chrome" in installer
