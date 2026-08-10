"""Minimal Cults3D GraphQL client (standard library only).

Endpoint : POST https://cults3d.com/graphql   (JSON: {query, variables})
Auth     : Authorization: Basic base64(API_USER:API_KEY)
Assets   : Cults3D does NOT accept file uploads. Images and 3D files must be
           passed as publicly reachable HTTPS URLs (imageUrls / fileUrls,
           max 10 each). See README "Connecting Cults3D".
Limits   : ~60 req / 30 s, ~500 / day -> exponential backoff on 429 / 5xx.

The API key is read from the environment by the adapter and is never logged.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

CULTS3D_ENDPOINT = "https://cults3d.com/graphql"
_VALID_ENUM = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ_")


class Cults3DError(Exception):
    """Raised for transport failures or GraphQL errors (message is safe to log)."""


@dataclass
class CreationResult:
    id: str
    url: str


def _enum_token(value: str, field: str) -> str:
    """Validate an enum token (e.g. locale EN, currency USD) to avoid injection."""
    token = (value or "").strip().upper()
    if not token or any(ch not in _VALID_ENUM for ch in token):
        raise Cults3DError(f"Invalid {field} value: {value!r}")
    return token


class Cults3DClient:
    def __init__(self, api_user: str, api_key: str,
                 endpoint: str = CULTS3D_ENDPOINT,
                 timeout: float = 30.0,
                 max_retries: int = 4,
                 sleep=time.sleep,
                 opener: urllib.request.OpenerDirector | None = None):
        if not api_user or not api_key:
            raise Cults3DError("Missing Cults3D credentials.")
        self._auth = base64.b64encode(f"{api_user}:{api_key}".encode()).decode()
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self._sleep = sleep
        self._opener = opener or urllib.request.build_opener()

    # -- transport ----------------------------------------------------------
    def _post(self, query: str, variables: dict) -> dict:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        last_err = "unknown error"
        for attempt in range(self.max_retries):
            req = urllib.request.Request(self.endpoint, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            req.add_header("Authorization", f"Basic {self._auth}")
            try:
                with self._opener.open(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                data = json.loads(body)
            except urllib.error.HTTPError as exc:
                status = exc.code
                if status == 429 or 500 <= status < 600:
                    last_err = f"HTTP {status}"
                    self._sleep(2 ** attempt)
                    continue
                detail = _safe_body(exc)
                raise Cults3DError(f"HTTP {status}: {detail}") from None
            except (urllib.error.URLError, TimeoutError) as exc:
                last_err = str(getattr(exc, "reason", exc))
                self._sleep(2 ** attempt)
                continue
            except json.JSONDecodeError:
                raise Cults3DError("Non-JSON response from Cults3D.") from None

            if data.get("errors"):
                msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
                raise Cults3DError(f"GraphQL error: {msgs}")
            return data.get("data", {})
        raise Cults3DError(f"Cults3D unreachable after {self.max_retries} tries ({last_err}).")

    # -- operations ---------------------------------------------------------
    def check_auth(self) -> bool:
        """Cheap authenticated call to confirm credentials work.

        `myself` requires authentication, so a GraphQL/HTTP error here means
        the credentials are wrong or missing.
        """
        self._post("query { myself { nick } }", {})
        return True

    def list_categories(self, locale: str = "EN") -> list[dict]:
        loc = _enum_token(locale, "locale")
        query = f"query {{ categories {{ id name(locale: {loc}) }} }}"
        data = self._post(query, {})
        return data.get("categories", []) or []

    def create_creation(self, *, name: str, description: str,
                        image_urls: list[str], file_urls: list[str],
                        locale: str, currency: str,
                        download_price: float | None,
                        category_id: str | None,
                        license_code: str | None,
                        tag_names: list[str]) -> CreationResult:
        loc = _enum_token(locale, "locale")
        cur = _enum_token(currency, "currency")

        # Enums (locale, currency) are inlined as validated tokens; everything
        # else travels as typed GraphQL variables.
        query = f"""
mutation CreateCreation(
  $name: String!, $description: String!,
  $imageUrls: [String!]!, $fileUrls: [String!]!,
  $categoryId: ID, $downloadPrice: Float,
  $licenseCode: String, $tagNames: [String!]
) {{
  createCreation(
    name: $name, description: $description,
    imageUrls: $imageUrls, fileUrls: $fileUrls,
    locale: {loc}, currency: {cur},
    categoryId: $categoryId, downloadPrice: $downloadPrice,
    licenseCode: $licenseCode, tagNames: $tagNames,
    madeWithAi: false
  ) {{
    creation {{ id url(locale: {loc}) }}
    errors
  }}
}}""".strip()

        variables = {
            "name": name,
            "description": description,
            "imageUrls": image_urls,
            "fileUrls": file_urls,
            "categoryId": category_id,
            "downloadPrice": download_price,
            "licenseCode": license_code,
            "tagNames": tag_names,
        }
        data = self._post(query, variables)
        node = (data or {}).get("createCreation") or {}
        errors = node.get("errors")
        if errors:
            raise Cults3DError(f"createCreation rejected: {errors}")
        creation = node.get("creation") or {}
        cid, url = creation.get("id"), creation.get("url")
        if not cid:
            raise Cults3DError("createCreation returned no creation id.")
        return CreationResult(id=str(cid), url=url or "")


def _safe_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8")[:300]
    except Exception:
        return exc.reason if hasattr(exc, "reason") else "error"
