"""Tiny HTTP helpers for social adapters (standard library only).

Kept in one place so tests can monkeypatch a single function per adapter and no
adapter needs a third-party HTTP dependency. Tokens are passed via headers by
the caller and are never logged here.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


class SocialHTTPError(Exception):
    pass


def _open(req, timeout: float = 30.0) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = getattr(exc, "reason", "error")
        raise SocialHTTPError(f"HTTP {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SocialHTTPError(str(getattr(exc, "reason", exc))) from None
    except json.JSONDecodeError:
        raise SocialHTTPError("Non-JSON response.") from None


def post_form(url: str, fields: dict, headers: dict | None = None) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    for key, val in (headers or {}).items():
        req.add_header(key, val)
    return _open(req)


def post_json(url: str, obj: dict, headers: dict | None = None) -> dict:
    data = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, val in (headers or {}).items():
        req.add_header(key, val)
    return _open(req)
