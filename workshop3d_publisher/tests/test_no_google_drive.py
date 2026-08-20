"""Publikowanie bez Google Drive for desktop.

Lustrzenie kilkuset gigabajtow modeli na dysk roboczy nie jest warunkiem
publikacji. Gdy klient Drive'a nie jest uruchomiony, obszarem roboczym jest
zwykly lokalny folder wrzutowy (``paths.ready_folder``) i jego siostrzany
``Opublikowane``; magazyn posprzedazowy na Nextcloud dziala jak wczesniej.
"""
from pathlib import Path

from workshop3d import cloud_mirror, cloud_sync
from workshop3d.dashboard.app import create_app
from workshop3d.models import ProductRecord
from workshop3d.state_store import StateStore


def _nextcloud(config, tmp_path):
    """Nextcloud jako folder lokalny - test nie wychodzi do sieci."""
    folder = tmp_path / "nextcloud"
    folder.mkdir(exist_ok=True)
    config.set("cloud_sync.enabled", True)
    config.set("cloud_sync.nextcloud.local_folder", str(folder))
    return folder


def _record(folder: Path) -> ProductRecord:
    return ProductRecord("prod-1", folder.name, str(folder))


def _pipeline(config, tmp_path):
    from workshop3d.pipeline import Pipeline

    return Pipeline(config, StateStore(tmp_path / "work" / "state.json"))


# ------------------------------------------------------------------ wybor nogi

def test_missing_desktop_client_falls_back_to_the_local_folder(config, tmp_path):
    assert cloud_sync.working_provider(config) == cloud_sync.PROVIDER_LOCAL
    assert cloud_sync.providers(config) == (cloud_sync.PROVIDER_LOCAL, "nextcloud")
    assert cloud_sync.working_root(config) == tmp_path


def test_present_desktop_client_is_still_used(config, tmp_path):
    drive = tmp_path / "Google FolderSync"
    drive.mkdir()
    config.set("cloud_sync.google_drive.local_folder", str(drive))

    assert cloud_sync.working_provider(config) == "google_drive"
    assert cloud_sync.working_root(config) == drive


def test_example_config_ships_with_the_google_leg_off(tmp_path):
    """Instalacja i aktualizacja maja nie wlaczac klienta Drive'a z powrotem."""
    from workshop3d.config import Config, EXAMPLE_CONFIG

    example = Config.load(EXAMPLE_CONFIG)

    assert cloud_sync.google_enabled(example) is False
    assert cloud_sync.working_provider(example) == cloud_sync.PROVIDER_LOCAL
    installer = (Path(__file__).resolve().parents[1] / "install.bat").read_text(
        encoding="utf-8"
    )
    assert "--configure-zero-touch" in installer


def test_google_leg_can_be_switched_off_explicitly(config, tmp_path):
    drive = tmp_path / "Google FolderSync"
    drive.mkdir()
    config.set("cloud_sync.google_drive.local_folder", str(drive))
    config.set("cloud_sync.google_drive.enabled", False)

    assert cloud_sync.working_provider(config) == cloud_sync.PROVIDER_LOCAL
    assert cloud_sync.working_root(config) == tmp_path


# ------------------------------------------------------------------- publikacja

def test_product_is_not_stuck_waiting_for_an_absent_drive(
    product_folder, config, tmp_path
):
    """Bez tego kazdy produkt czekalby w kolejce na klienta, ktorego nie ma."""
    _nextcloud(config, tmp_path)
    source = product_folder(name="Castle Doflot")

    result = cloud_sync.sync_product(_record(source), config)

    assert result["status"] == "SYNCED"
    assert "google_drive" not in result["targets"]
    assert result["targets"][cloud_sync.PROVIDER_LOCAL]["status"] == "IN_PLACE"
    assert result["targets"]["nextcloud"]["status"] == "COPIED_LOCAL"
    assert result["next_retry_at"] is None


def test_local_folder_is_not_copied_onto_itself(product_folder, config, tmp_path):
    _nextcloud(config, tmp_path)
    source = product_folder(name="Castle Doflot")
    before = sorted(path.name for path in source.iterdir())

    cloud_sync.sync_product(_record(source), config)

    assert sorted(path.name for path in source.iterdir()) == before
    assert not (tmp_path / "ready" / "ready").exists()


def test_finished_product_leaves_the_drop_folder(product_folder, config, tmp_path):
    nextcloud = _nextcloud(config, tmp_path)
    source = product_folder(name="Castle Doflot")
    record = _record(source)
    cloud_sync.sync_product(record, config)

    result = cloud_sync.archive_product(record, config)

    published = tmp_path / "Opublikowane" / "Castle Doflot"
    assert result["status"] == "ARCHIVED"
    assert not source.exists()
    assert (published / "Castle Doflot.stl").is_file()
    # Rekord idzie za folderem, dokladnie jak przy Google Drive.
    assert record.folder_path == str(published)
    assert (nextcloud / "Opublikowane" / "Castle Doflot").is_dir()
    assert not (nextcloud / "Gotowe do sklepu" / "Castle Doflot").exists()


def test_archive_move_is_idempotent(product_folder, config, tmp_path):
    _nextcloud(config, tmp_path)
    source = product_folder(name="Castle Doflot")
    record = _record(source)
    cloud_sync.sync_product(record, config)
    cloud_sync.archive_product(record, config)

    again = cloud_sync.archive_product(record, config)

    assert again["status"] == "ARCHIVED"
    assert again["targets"][cloud_sync.PROVIDER_LOCAL]["status"] == "ALREADY_MOVED"
    assert list((tmp_path / "Opublikowane").iterdir()) == [
        tmp_path / "Opublikowane" / "Castle Doflot"
    ]


def test_full_run_finishes_without_google_drive(product_folder, config, tmp_path):
    """Objaw bledu: produkt konczyl w AWAITING_CLOUD_SYNC i czekal bez konca."""
    from workshop3d.models import State

    nextcloud = _nextcloud(config, tmp_path)
    folder = product_folder(name="Cloud Completion")

    record = _pipeline(config, tmp_path).on_folder_ready(folder)

    assert record.state in (
        State.COMPLETED.value,
        State.COMPLETED_WITH_WARNINGS.value,
    )
    assert record.cloud_sync["status"] == "SYNCED"
    assert record.cloud_archive["status"] == "ARCHIVED"
    assert record.completed_at is not None
    assert record.folder_path == str(tmp_path / "Opublikowane" / folder.name)
    assert not folder.exists()
    assert (nextcloud / "Opublikowane" / folder.name).is_dir()


# ----------------------------------------------------------------------- lustro

def test_mirror_pushes_the_local_archive_to_nextcloud(config, tmp_path):
    nextcloud = _nextcloud(config, tmp_path)
    archived = tmp_path / "Opublikowane" / "Sold Product" / "model.stl"
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"sold")
    in_progress = tmp_path / "ready" / "Work In Progress" / "model.stl"
    in_progress.parent.mkdir(parents=True)
    in_progress.write_bytes(b"not ready yet")

    result = cloud_mirror.sync_once(config, tmp_path / "mirror.json")

    assert result["status"] == "SYNCED"
    assert result["direction"] == cloud_mirror.DIRECTION_ONE_WAY
    assert (nextcloud / "Opublikowane" / "Sold Product" / "model.stl").read_bytes() == b"sold"
    # Praca w toku zostaje lokalnie; magazyn dostaje tylko Opublikowane.
    assert not (nextcloud / "ready").exists()
    assert result["copied_google_to_nextcloud"] == 1


# ----------------------------------------------------------------------- panel

def test_dashboard_points_at_the_local_drop_folder(config, tmp_path):
    """Panel nie moze reklamowac folderu Google, ktorego nikt nie napelnia."""
    store = StateStore(tmp_path / "work" / "state.json")
    page = create_app(config, store).test_client().get("/")

    assert page.status_code == 200
    body = page.data.decode("utf-8")
    assert "Folder na tym komputerze" in body
    assert str((tmp_path / "ready").resolve()) in body
    assert "Google Folder Sync" not in body
