from workshop3d.config import Config
from workshop3d.dashboard.app import create_app
from workshop3d.state_store import StateStore


def _app(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        f"paths: {{ready_folder: '{tmp_path / 'ready'}', work_folder: '{tmp_path / 'work'}'}}\n"
        "modes: {dry_run: true, auto_publish: false}\n",
        encoding="utf-8",
    )
    config = Config.load(cfg_file)
    store = StateStore(tmp_path / "state.json")
    return create_app(config, store), tmp_path / "work" / "listings.json"


def test_listing_page_can_save_and_render_exports(tmp_path):
    app, listings_file = _app(tmp_path)
    client = app.test_client()

    response = client.post("/listings", data={
        "title_pl": "Brama lochu",
        "title_en": "Dungeon Gate",
        "description_pl": "Polski opis",
        "description_en": "English description",
        "tags": "dungeon, gate, dungeon, terrain",
        "link_printables": "https://printables.com/model/123",
    })

    assert response.status_code in (301, 302)
    assert listings_file.exists()

    page = client.get("/listings")
    assert page.status_code == 200
    assert b"Dungeon Gate" in page.data
    assert b"Printables" in page.data
    assert b"English description" in page.data
