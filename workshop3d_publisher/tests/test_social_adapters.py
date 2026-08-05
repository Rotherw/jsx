"""Social adapters: store tagging + Mastodon/Bluesky wiring (no real network)."""
from workshop3d.config import Config
from workshop3d.state_store import StateStore
from workshop3d.pipeline import Pipeline
from workshop3d.models import ProductRecord, SocialResult
from workshop3d.adapters.base import compose_post
from workshop3d.adapters.social.mastodon import MastodonAdapter
from workshop3d.adapters.social.bluesky import BlueskyAdapter


def _record_with_stores(*, cults=True, thangs=True):
    rec = ProductRecord(product_id="p1", folder_name="Door", folder_path="/x")
    rec.metadata = {
        "SOCIAL_MEDIA_TEXTS": {
            "facebook": {"text": "Nowy model: Door!", "hashtags": "#workshop3d"},
            "mastodon": {"text": "Door - new model.", "hashtags": "#workshop3d"},
            "bluesky": {"text": "Door - new model.", "hashtags": "#workshop3d"},
        }
    }
    if cults:
        rec.stores["cults3d"] = {"status": "DRY_RUN", "url": "https://cults3d.com/x"}
    if thangs:
        rec.stores["thangs"] = {"status": "STAGED", "url": "https://thangs.com/designer/WorkShop3D"}
    return rec


def test_store_tags_included_for_live_stores():
    config = Config({
        "modes": {"dry_run": True},
        "social": {"facebook": {"enabled": True},
                   "store_handles": {"cults3d": "@cults3d", "thangs": "@thangs3d"}},
        "stores": {"cults3d": {"enabled": True}},
        "links": {"main_link_priority": ["cults3d"]},
    })
    from workshop3d import publication_manager as pm
    rec = _record_with_stores()
    pm.promote_social(rec, config, "")
    assert rec.metadata["ACTIVE_STORE_TAGS"] == "@cults3d @thangs3d"

    body = compose_post(rec, "facebook", "https://cults3d.com/x")
    assert "@cults3d" in body and "@thangs3d" in body


def test_creality_handle_deduplicated():
    config = Config({"social": {"store_handles": {
        "creality_cloud_eu": "@CrealityCloud", "creality_cloud_cn": "@CrealityCloud"}}})
    rec = ProductRecord(product_id="p", folder_name="f", folder_path="/x")
    rec.stores["creality_cloud_eu"] = {"status": "STAGED"}
    rec.stores["creality_cloud_cn"] = {"status": "STAGED"}
    from workshop3d.publication_manager import _store_tags
    assert _store_tags(rec, config) == "@CrealityCloud"


def test_mastodon_dry_run_and_not_connected(monkeypatch):
    dry = Config({"modes": {"dry_run": True}})
    rec = _record_with_stores()
    rec.metadata["ACTIVE_STORE_TAGS"] = "@cults3d"
    assert MastodonAdapter(dry, {}).post(rec, "https://x", "").status == "DRY_RUN"

    live = Config({"modes": {"dry_run": False}})
    monkeypatch.delenv("MASTODON_INSTANCE_URL", raising=False)
    monkeypatch.delenv("MASTODON_ACCESS_TOKEN", raising=False)
    assert MastodonAdapter(live, {}).post(rec, "https://x", "").status == "NOT_CONNECTED"


def test_mastodon_real_post_mocked(monkeypatch):
    live = Config({"modes": {"dry_run": False}})
    monkeypatch.setenv("MASTODON_INSTANCE_URL", "https://mastodon.social")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "tok")
    rec = _record_with_stores()
    rec.metadata["ACTIVE_STORE_TAGS"] = "@cults3d @thangs3d"

    captured = {}
    import workshop3d.adapters.social.mastodon as mod

    def fake_post_form(url, fields, headers=None):
        captured["url"] = url
        captured["fields"] = fields
        captured["headers"] = headers
        return {"url": "https://mastodon.social/@w3d/1"}

    monkeypatch.setattr(mod, "post_form", fake_post_form)
    res = MastodonAdapter(live, {}).post(rec, "https://cults3d.com/x", "")
    assert res.status == "POSTED"
    assert res.post_url.endswith("/1")
    assert captured["url"].endswith("/api/v1/statuses")
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert "@cults3d" in captured["fields"]["status"]


def test_bluesky_real_post_mocked(monkeypatch):
    live = Config({"modes": {"dry_run": False}})
    monkeypatch.setenv("BLUESKY_HANDLE", "workshop3d.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "app-pass")
    rec = _record_with_stores()
    rec.metadata["ACTIVE_STORE_TAGS"] = "@cults3d"

    import workshop3d.adapters.social.bluesky as mod
    calls = []

    def fake_post_json(url, obj, headers=None):
        calls.append(url)
        if url.endswith("createSession"):
            return {"accessJwt": "jwt", "did": "did:plc:abc"}
        return {"uri": "at://did:plc:abc/app.bsky.feed.post/xyz123"}

    monkeypatch.setattr(mod, "post_json", fake_post_json)
    res = BlueskyAdapter(live, {}).post(rec, "https://cults3d.com/x", "")
    assert res.status == "POSTED"
    assert res.post_url == "https://bsky.app/profile/workshop3d.bsky.social/post/xyz123"
    assert any("createSession" in c for c in calls) and any("createRecord" in c for c in calls)


def test_all_social_networks_registered():
    from workshop3d.adapters.base import _SOCIAL
    for key in ["facebook", "instagram", "x", "pinterest", "mastodon", "bluesky", "tiktok", "youtube"]:
        assert key in _SOCIAL
