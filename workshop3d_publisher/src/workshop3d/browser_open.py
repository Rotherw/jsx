"""Open Publisher pages in the user's installed Google Chrome."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


def find_chrome() -> Path | None:
    """Return the real Chrome executable, preferring the current-user install."""
    if not sys.platform.startswith("win"):
        found = shutil.which("google-chrome") or shutil.which("chrome")
        return Path(found) if found else None

    candidates: list[Path] = []
    for env_name in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(
                Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"
            )
    found = shutil.which("chrome.exe") or shutil.which("chrome")
    if found:
        candidates.append(Path(found))

    try:
        import winreg

        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(
                    hive,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                ) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if value:
                        candidates.append(Path(value))
            except OSError:
                continue
    except ImportError:
        pass

    return next((path for path in candidates if path.is_file()), None)


def open_in_chrome(url: str) -> bool:
    """Open a URL in Chrome; use the system default only if Chrome is absent."""
    chrome = find_chrome()
    if chrome is not None:
        try:
            subprocess.Popen([str(chrome), url])
            return True
        except OSError:
            pass
    try:
        controller = webbrowser.get("chrome")
        return bool(controller.open(url))
    except webbrowser.Error:
        return bool(webbrowser.open(url))
