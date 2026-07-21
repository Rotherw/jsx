"""Fact card + metadata generation without inventing data (spec 23)."""
from pathlib import Path

from workshop3d.file_validator import validate
from workshop3d.product_analyzer import build_fact_card
from workshop3d.metadata_generator import generate


def _prep(folder, config):
    v = validate(folder)
    fc = build_fact_card(folder, v, config)
    md = generate(folder, v, fc, config)
    return v, fc, md


def test_fact_card_splits_known_unknown(product_folder, config):
    folder = product_folder(name="Dark Fantasy Dungeon Door")
    _, fc, _ = _prep(folder, config)
    assert fc["product_type"] == "terrain"       # "door" keyword
    assert any("STL files delivered" in c for c in fc["confirmed"])
    # Must NOT invent scale / print time / material.
    joined = " ".join(fc["unknown"]).lower()
    for forbidden in ["scale", "print time", "material", "supports"]:
        assert forbidden in joined


def test_metadata_no_fabricated_print_claims(product_folder, config):
    folder = product_folder()
    _, _, md = _prep(folder, config)
    desc = md["DESCRIPTION_EN"].lower()
    # No unfounded promises.
    for banned in ["tested", "no supports", "without supports", "ready for resin", "1:", "scale"]:
        assert banned not in desc
    assert md["DESCRIPTION_EN"].strip().endswith("Rafal z WorkShop3D")


def test_exactly_20_tags_when_allowed(product_folder, config):
    folder = product_folder(name="Fallathan Dungeon Door")
    _, _, md = _prep(folder, config)
    assert len(md["TAGS"]) == 20
    assert "workshop3d" in md["TAGS"]


def test_collection_only_when_matched(product_folder, config):
    plain = product_folder(name="Simple Barrel Prop")
    _, fc, _ = _prep(plain, config)
    assert fc["collection"] is None                # not auto-tagged into a series

    fall = product_folder(name="Fallathan Gate")
    _, fc2, _ = _prep(fall, config)
    assert fc2["collection"]["id"] == "kroniki_fallathanu"


def test_title_has_no_extensions_and_slug_is_ascii(product_folder, config):
    folder = product_folder(name="Smok Zloty")
    _, _, md = _prep(folder, config)
    assert ".stl" not in md["TITLE"].lower()
    assert md["SLUG"].isascii()
    assert " " not in md["SLUG"]


def test_bundle_pricing(product_folder, config):
    folder = product_folder(name="Village Bundle", extra_stl=2)
    _, fc, md = _prep(folder, config)
    assert fc["product_type"] == "bundle"
    assert md["PRICE"]["amount"] == 13.99


def test_renamed_copies_are_ascii_underscore(product_folder, config):
    folder = product_folder(name="Zolty Smok")
    _, _, md = _prep(folder, config)
    for new in md["RENAMED_FILES"].values():
        stem = new.rsplit(".", 1)[0]
        assert stem.replace("_", "").isalnum()
