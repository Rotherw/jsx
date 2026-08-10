"""Real-HTTP social adapters (FB, IG, Pinterest, X) with mocked transport."""
import pytest

from workshop3d.config import Config
from workshop3d.models import ProductRecord
from workshop3d.adapters.social.facebook import FacebookAdapter
from workshop3d.adapters.social.instagram import InstagramAdapter
from workshop3d.adapters.social.pinterest import PinterestAdapter
from workshop3d.adapters.social.x_twitter import XAdapter


def _record():
    rec = ProductRecord(product_id="p1", folder_name="Door", folder_path="/x")
    rec.metadata = {
        "TITLE": "Dungeon Door",
        "SOCIAL_MEDIA_TEXTS": {
            "facebook": {"text": "Nowy: Door", "hashtags": "#w3d"},
            "instagram": {"text": "Door", "hashtags": "#w3d"},
            "pinterest": {"text": "Door", "hashtags": "#w3d"},
            "x": {"text": "Door", "hashtags": "#w3d"},
        },
        "ACTIVE_STORE_TAGS": "@cults3d",
    }
    return rec


def _live():
    return Config({"modes": {"dry_run": False}, "social": {"image_host": "google_drive"}})


def test_facebook_real_post(monkeypatch):
    monkeypatch.setenv("FB_PAGE_ID", "123")
    monkeypatch.setenv("FB_PAGE_TOKEN", "tok")
    import workshop3d.adapters.social.facebook as mod
    cap = {}
    def fake(url, fields, headers=None):
        cap["url"] = url; cap["fields"] = fields
        return {"id": "123_456"}
    monkeypatch.setattr(mod, "post_form", fake)
    res = FacebookAdapter(_live(), {}).post(_record(), "https://cults3d.com/x", "")
    assert res.status == "POSTED" and res.post_url.endswith("123_456")
    assert cap["url"].endswith("/123/feed")
    assert cap["fields"]["link"] == "https://cults3d.com/x"
    assert "@cults3d" in cap["fields"]["message"]


def test_instagram_two_step(monkeypatch, tmp_path):
    monkeypatch.setenv("IG_USER_ID", "999")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "tok")
    import workshop3d.adapters.social.instagram as mod
    monkeypatch.setattr(mod, "hosted_cover_url", lambda r, c, w: "https://img/cover.png")
    calls = []
    def fake(url, fields, headers=None):
        calls.append(url)
        return {"id": "cid"} if url.endswith("/media") else {"id": "mediaXYZ"}
    monkeypatch.setattr(mod, "post_form", fake)
    res = InstagramAdapter(_live(), {}).post(_record(), "https://cults3d.com/x", str(tmp_path))
    assert res.status == "POSTED"
    assert any(u.endswith("/media") for u in calls) and any(u.endswith("/media_publish") for u in calls)


def test_instagram_needs_public_image(monkeypatch, tmp_path):
    monkeypatch.setenv("IG_USER_ID", "999")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "tok")
    import workshop3d.adapters.social.instagram as mod
    monkeypatch.setattr(mod, "hosted_cover_url", lambda r, c, w: None)
    res = InstagramAdapter(_live(), {}).post(_record(), "https://cults3d.com/x", str(tmp_path))
    assert res.status == "NEEDS_ATTENTION"


def test_pinterest_real_pin(monkeypatch, tmp_path):
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("PINTEREST_BOARD_ID", "board1")
    import workshop3d.adapters.social.pinterest as mod
    monkeypatch.setattr(mod, "hosted_cover_url", lambda r, c, w: "https://img/cover.png")
    cap = {}
    def fake(url, obj, headers=None):
        cap["url"] = url; cap["obj"] = obj; cap["headers"] = headers
        return {"id": "pin789"}
    monkeypatch.setattr(mod, "post_json", fake)
    res = PinterestAdapter(_live(), {}).post(_record(), "https://cults3d.com/x", str(tmp_path))
    assert res.status == "POSTED" and res.post_url.endswith("pin789")
    assert cap["obj"]["board_id"] == "board1"
    assert cap["obj"]["media_source"]["url"] == "https://img/cover.png"
    assert cap["headers"]["Authorization"] == "Bearer tok"


def test_x_real_tweet(monkeypatch):
    for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        monkeypatch.setenv(k, "v")
    import workshop3d.adapters.social.x_twitter as mod
    cap = {}
    def fake(url, obj, headers=None):
        cap["url"] = url; cap["obj"] = obj; cap["headers"] = headers
        return {"data": {"id": "tweet42"}}
    monkeypatch.setattr(mod, "post_json", fake)
    res = XAdapter(_live(), {}).post(_record(), "https://cults3d.com/x", "")
    assert res.status == "POSTED" and res.post_url.endswith("tweet42")
    assert cap["headers"]["Authorization"].startswith("OAuth ")
    assert "@cults3d" in cap["obj"]["text"]


def test_all_wired_not_connected_without_creds(monkeypatch):
    for k in ["FB_PAGE_ID", "FB_PAGE_TOKEN", "IG_USER_ID", "IG_ACCESS_TOKEN",
              "PINTEREST_ACCESS_TOKEN", "PINTEREST_BOARD_ID",
              "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]:
        monkeypatch.delenv(k, raising=False)
    live = _live()
    for adapter in (FacebookAdapter, InstagramAdapter, PinterestAdapter, XAdapter):
        assert adapter(live, {}).post(_record(), "https://x", "").status == "NOT_CONNECTED"
