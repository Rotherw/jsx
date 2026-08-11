"""Publisher URLs always prefer the user's normal Google Chrome."""
from workshop3d import browser_open


def test_windows_chrome_is_found_and_used(tmp_path, monkeypatch):
    local = tmp_path / "Local"
    chrome = local / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_bytes(b"exe")
    monkeypatch.setattr(browser_open.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.delenv("PROGRAMFILES", raising=False)
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)
    monkeypatch.setattr(browser_open.shutil, "which", lambda _name: None)
    calls = []
    monkeypatch.setattr(
        browser_open.subprocess,
        "Popen",
        lambda command: calls.append(command),
    )

    assert browser_open.find_chrome() == chrome
    assert browser_open.open_in_chrome("https://cloud.workshop3d.pl") is True
    assert calls == [[str(chrome), "https://cloud.workshop3d.pl"]]
