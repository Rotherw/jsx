"""System notifications (spec section 18).

Shows a Windows toast when possible, always logs to stdout as a fallback so
the pipeline works on any OS / in tests.
"""
from __future__ import annotations


def notify(title: str, message: str) -> None:
    print(f"[NOTIFY] {title}: {message}")
    try:
        from plyer import notification  # type: ignore

        notification.notify(title=title, message=message, app_name="WorkShop3D Publisher", timeout=8)
    except Exception:
        # plyer not installed or no desktop session -> stdout fallback is enough.
        pass
