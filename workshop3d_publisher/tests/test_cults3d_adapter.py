"""Cults3D adapter + GraphQL client tests (no real network calls)."""
import io
import json

import pytest

from workshop3d.config import Config
from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.models import ProductRecord
from workshop3d.adapters.stores.cults3d import Cults3DAdapter
from workshop3d.adapters.stores._cults_api import Cults3DClient, Cults3DError


# --- a fake urllib opener so we can assert on the request without a network ---
class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class FakeOpener:
    def __init__(self, response_payload, capture):
        self._payload = response_payload
        self._capture = capture

    def open(self, req, timeout=None):
        self._capture["url"] = req.full_url
        self._capture["method"] = req.get_method()
        self._capture["headers"] = dict(req.header_items())
        self._capture["body"] = json.loads(req.data.decode())
        return FakeResponse(json.dumps(self._payload).encode())


def test_client_sends_basic_auth_and_parses_creation():
    capture = {}
    payload = {"data": {"createCreation": {"creation": {"id": "abc123",
              "url": "https://cults3d.com/en/3d-model/x"}, "errors": None}}}
    client = Cults3DClient("user", "key", opener=FakeOpener(payload, capture), sleep=lambda s: None)
    res = client.create_creation(
        name="Test", description="desc", image_urls=["https://h/x.png"],
        file_urls=["https://h/x.stl"], locale="EN", currency="USD",
        download_price=4.99, category_id="7", license_code="lic", tag_names=["a", "b"],
    )
    assert res.id == "abc123"
    # Basic auth header present (base64 of user:key) and never the raw key.
    auth = capture["headers"].get("Authorization", "")
    assert auth.startswith("Basic ")
    assert "key" not in auth
    # Enums inlined, variables carry the rest.
    assert "locale: EN" in capture["body"]["query"]
    assert capture["body"]["variables"]["downloadPrice"] == 4.99


def test_client_raises_on_graphql_errors():
    client = Cults3DClient("u", "k",
                           opener=FakeOpener({"errors": [{"message": "bad token"}]}, {}),
                           sleep=lambda s: None)
    with pytest.raises(Cults3DError):
        client.check_auth()


def test_client_rejects_bad_enum():
    client = Cults3DClient("u", "k", opener=FakeOpener({"data": {}}, {}), sleep=lambda s: None)
    with pytest.raises(Cults3DError):
        client.create_creation(name="n", description="d", image_urls=["u"], file_urls=["f"],
                               locale="EN; DROP", currency="USD", download_price=1.0,
                               category_id=None, license_code=None, tag_names=[])


def _live_config(tmp_path, asset_base_url=""):
    data = {
        "paths": {"ready_folder": str(tmp_path / "ready"), "work_folder": str(tmp_path / "work")},
        "modes": {"dry_run": False, "auto_publish": True, "require_approval": False},
        "trigger": {"stability_delay_seconds": 0, "stability_checks": 1,
                    "seconds_between_checks": 0, "ignore_patterns": []},
        "retry": {"max_attempts": 1, "backoff_seconds": [0]},
        "brand": {"name": "WorkShop3D", "signature": "Regards.\nRafal z WorkShop3D", "collections": []},
        "pricing": {"currency": "USD", "single_model": 4.99, "bundle_small": 13.99, "free_products": False},
        "licensing": {"default": {"owner": "WorkShop3D", "summary": "No redistribution."}},
        "categories": {"default": "terrain", "keyword_map": {"door": "terrain"}},
        "stores": {"cults3d": {"enabled": True, "mode": "api",
                               "asset_base_url": asset_base_url}},
        "social": {},
        "links": {"main_link_priority": ["cults3d"]},
    }
    return Config(data)


def test_live_without_credentials_is_not_connected(product_folder, tmp_path, monkeypatch):
    monkeypatch.delenv("CULTS3D_API_USER", raising=False)
    monkeypatch.delenv("CULTS3D_API_KEY", raising=False)
    config = _live_config(tmp_path)
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["cults3d"]["status"] == "NOT_CONNECTED"


def test_live_without_asset_base_url_needs_attention(product_folder, tmp_path, monkeypatch):
    monkeypatch.setenv("CULTS3D_API_USER", "u")
    monkeypatch.setenv("CULTS3D_API_KEY", "k")
    config = _live_config(tmp_path, asset_base_url="")   # no public host configured
    store = StateStore(tmp_path / "work" / "state.json")
    rec = Pipeline(config, store).on_folder_ready(product_folder())
    assert rec.stores["cults3d"]["status"] == "NEEDS_ATTENTION"
    assert "public" in rec.stores["cults3d"]["message"].lower()


def test_live_publish_success_with_mocked_client(product_folder, tmp_path, monkeypatch):
    monkeypatch.setenv("CULTS3D_API_USER", "u")
    monkeypatch.setenv("CULTS3D_API_KEY", "k")
    config = _live_config(tmp_path, asset_base_url="https://host.example/w3d")
    store = StateStore(tmp_path / "work" / "state.json")

    # Mock the network layer only; adapter logic runs for real.
    from workshop3d.adapters.stores import cults3d as mod

    class FakeClient:
        def __init__(self, *a, **k): pass
        def list_categories(self, locale="EN"): return [{"id": "42", "name": "Terrains"}]
        def create_creation(self, **kw):
            from workshop3d.adapters.stores._cults_api import CreationResult
            FakeClient.captured = kw
            return CreationResult(id="live99", url="https://cults3d.com/en/3d-model/live")

    monkeypatch.setattr(mod, "Cults3DClient", FakeClient)
    rec = Pipeline(config, store).on_folder_ready(product_folder())

    assert rec.stores["cults3d"]["status"] == "PUBLISHED"
    assert rec.stores["cults3d"]["listing_id"] == "live99"
    assert rec.stores["cults3d"]["url"].endswith("/live")
    # category "terrain" resolved to Cults "Terrains" id, and real asset URLs used.
    assert FakeClient.captured["category_id"] == "42"
    assert all(u.startswith("https://host.example/w3d/") for u in FakeClient.captured["file_urls"])
    # file_selection defaults to "zip" -> the model URL points at the package ZIP.
    assert any(u.endswith(".zip") for u in FakeClient.captured["file_urls"])
    assert FakeClient.captured["image_urls"]
