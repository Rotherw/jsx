"""Wiki KF2 matching is conservative and enrichment stays source-labelled."""
from workshop3d.config import Config
from workshop3d.wiki_client import WikiKF2Client, WikiMatch, enrich_metadata


def _client():
    return WikiKF2Client(Config({"wiki": {"minimum_match_score": 0.78}}))


def test_exact_title_with_file_and_scale_noise_matches(monkeypatch):
    client = _client()
    monkeypatch.setattr(client, "_search", lambda query: [
        {"title": "Czerwony Smok", "description": "", "path": "bestiariusz/czerwony-smok"},
        {"title": "Czarny Smok", "description": "", "path": "bestiariusz/czarny-smok"},
    ])
    monkeypatch.setattr(client, "_page_excerpt", lambda url: "Pewny opis z artykułu.")

    match = client.find("WorkShop3D Czerwony Smok STL 75mm")
    assert match is not None
    assert match.title == "Czerwony Smok"
    assert match.score == 1.0
    assert match.url.endswith("/bestiariusz/czerwony-smok")


def test_ambiguous_generic_name_is_rejected(monkeypatch):
    client = _client()
    monkeypatch.setattr(client, "_search", lambda query: [
        {"title": "Czerwony Smok", "path": "a"},
        {"title": "Czarny Smok", "path": "b"},
    ])
    assert client.find("Smok STL") is None


def test_metadata_names_source_and_does_not_claim_translation():
    metadata = {"DESCRIPTION_PL": "Opis produktu.", "DESCRIPTION_EN": "Product description."}
    match = WikiMatch(
        title="Czerwony Smok",
        description="",
        path="bestiariusz/czerwony-smok",
        url="https://wiki.kf2.pl/bestiariusz/czerwony-smok",
        excerpt="Opis świata.",
        score=1.0,
    )
    result = enrich_metadata(metadata, match)
    assert "Opis świata" in result["DESCRIPTION_PL"]
    assert match.url in result["DESCRIPTION_PL"]
    assert match.url in result["DESCRIPTION_EN"]
    assert result["WIKI_KF2"]["score"] == 1.0
