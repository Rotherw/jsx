"""OAuth 1.0a HMAC-SHA1 signing (standard library only) for the X/Twitter API.

Correctness is pinned by a unit test against X's own documented example
(see tests/test_x_oauth1.py).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import urllib.parse


def _pct(value: str) -> str:
    # RFC 3986 unreserved set is A-Za-z0-9-._~ ; everything else is encoded.
    return urllib.parse.quote(str(value), safe="~")


def signature_base_string(method: str, url: str, params: dict) -> str:
    encoded = sorted((_pct(k), _pct(v)) for k, v in params.items())
    param_str = "&".join(f"{k}={v}" for k, v in encoded)
    return "&".join([method.upper(), _pct(url), _pct(param_str)])


def sign(method: str, url: str, params: dict, consumer_secret: str, token_secret: str) -> str:
    base = signature_base_string(method, url, params)
    key = f"{_pct(consumer_secret)}&{_pct(token_secret)}".encode()
    digest = hmac.new(key, base.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def auth_header(method: str, url: str, *, consumer_key: str, consumer_secret: str,
                token: str, token_secret: str, nonce: str, timestamp: str,
                extra_params: dict | None = None) -> str:
    """Build the `Authorization: OAuth ...` header value.

    extra_params are request parameters that participate in the signature
    (query string or form body). For a JSON body (X API v2) pass none.
    """
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    all_params = dict(oauth)
    if extra_params:
        all_params.update(extra_params)
    oauth["oauth_signature"] = sign(method, url, all_params, consumer_secret, token_secret)
    parts = ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))
    return "OAuth " + parts
