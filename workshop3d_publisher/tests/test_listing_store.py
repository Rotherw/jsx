from workshop3d.listing_store import ListingRecord, export_payload, listing_warnings, parse_tags


def test_tags_are_deduplicated_and_exports_respect_limits():
    record = ListingRecord(
        listing_id="forest-gate",
        slug="forest-gate",
        title_pl="Brama lasu",
        title_en="Forest Gate",
        description_pl="Opis",
        description_en="Description",
        tags=parse_tags("forest, gate, forest, ruins, dungeon, tabletop, terrain, scatter, fantasy, printable, stl, workshop3d, rpg, dnd, resin, fdm, walls"),
    )

    exports = export_payload(record)

    assert record.tags[:3] == ["forest", "gate", "ruins"]
    printables = next(item for item in exports if item["key"] == "printables")
    assert len(printables["tags"]) == 15
    assert printables["warnings"] == ["Ucięto tagi do limitu 15."]


def test_listing_warnings_flag_brand_typos_and_broken_links():
    record = ListingRecord(
        listing_id="broken",
        slug="broken",
        title_pl="WorShop3D Brama",
        title_en="Forest Gate",
        description_pl="Opis",
        description_en="Description",
        tags=["forest"],
        links={"printables": "@printables", "thangs": "ftp://broken"},
    )

    warnings = listing_warnings(record)

    assert any("WorShop3D" in item for item in warnings)
    assert any("sam handle" in item for item in warnings)
    assert any("niepoprawny link" in item for item in warnings)
