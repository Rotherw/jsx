"""Finished-folder synchronisation to the exact Google and Nextcloud inboxes."""
from workshop3d import cloud_sync
from workshop3d.models import ProductRecord


def _configure(config, tmp_path):
    google = tmp_path / "Google FolderSync"
    nextcloud = tmp_path / "Nextcloud Folder Sync"
    config.set("cloud_sync.enabled", True)
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.local_folder", str(nextcloud))
    return google, nextcloud


def test_same_finished_folder_goes_to_both_clouds(
    product_folder, config, tmp_path
):
    google, nextcloud = _configure(config, tmp_path)
    source = product_folder(name="Forest Gate")
    nested = source / "parts"
    nested.mkdir()
    (nested / "notes.txt").write_text("nested", encoding="utf-8")
    record = ProductRecord("prod-id-must-not-be-folder", source.name, str(source))

    result = cloud_sync.sync_product(record, config)

    assert result["status"] == "SYNCED"
    for root in (google, nextcloud):
        target = root / "Gotowe do sklepu" / "Forest Gate"
        assert (target / "Forest Gate.png").is_file()
        assert (target / "Forest Gate.stl").is_file()
        assert (target / "parts" / "notes.txt").read_text() == "nested"
        assert not (target / "sync_manifest.json").exists()
        assert not (root / "Gotowe do sklepu" / record.product_id).exists()


def test_google_inbox_source_is_not_duplicated(product_folder, config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    inbox = google / "Gotowe do sklepu"
    source = product_folder(name="Only One Folder", root=inbox)
    record = ProductRecord("abc123", source.name, str(source))

    result = cloud_sync.sync_product(record, config)

    assert result["status"] == "SYNCED"
    assert [path.name for path in inbox.iterdir()] == ["Only One Folder"]
    assert (nextcloud / "Gotowe do sklepu" / "Only One Folder").is_dir()


def test_unavailable_desktop_folders_wait_and_schedule_retry(
    product_folder, config, tmp_path
):
    source = product_folder(name="Waiting Cloud")
    google_file = tmp_path / "google-is-a-file"
    nextcloud_file = tmp_path / "nextcloud-is-a-file"
    google_file.write_text("x")
    nextcloud_file.write_text("x")
    config.set("cloud_sync.enabled", True)
    config.set("cloud_sync.google_drive.local_folder", str(google_file))
    config.set("cloud_sync.nextcloud.local_folder", str(nextcloud_file))
    record = ProductRecord("waiting", source.name, str(source))

    result = cloud_sync.sync_product(record, config)

    assert result["status"] == "WAITING"
    assert result["next_retry_at"] is not None
    assert all(item["status"] == "WAITING" for item in result["targets"].values())


def test_completed_folder_moves_to_sibling_published_without_duplicate(
    product_folder, config, tmp_path
):
    google, nextcloud = _configure(config, tmp_path)
    source = product_folder(
        name="Move After Publish", root=google / "Gotowe do sklepu"
    )
    record = ProductRecord("move-id", source.name, str(source))
    assert cloud_sync.sync_product(record, config)["status"] == "SYNCED"

    archived = cloud_sync.archive_product(record, config)

    assert archived["status"] == "ARCHIVED"
    for root in (google, nextcloud):
        assert not (root / "Gotowe do sklepu" / source.name).exists()
        assert (root / "Opublikowane" / source.name / f"{source.name}.stl").is_file()
        assert len(list((root / "Opublikowane").glob(source.name))) == 1
    assert record.folder_path == str(google / "Opublikowane" / source.name)

    again = cloud_sync.archive_product(record, config)
    assert again["status"] == "ARCHIVED"
    assert all(
        target["status"] == "ALREADY_MOVED" for target in again["targets"].values()
    )


def test_partial_archive_retries_without_recreating_ready_folder(
    product_folder, config, tmp_path
):
    google, nextcloud = _configure(config, tmp_path)
    source = product_folder(name="Retry Move", root=google / "Gotowe do sklepu")
    record = ProductRecord("retry-move", source.name, str(source))
    record.cloud_sync = cloud_sync.sync_product(record, config)
    blocked = tmp_path / "blocked-nextcloud"
    blocked.write_text("file")
    config.set("cloud_sync.nextcloud.local_folder", str(blocked))

    first = cloud_sync.archive_product(record, config)
    record.cloud_archive = first
    assert first["status"] == "WAITING"
    assert (google / "Opublikowane" / source.name).is_dir()
    assert not (google / "Gotowe do sklepu" / source.name).exists()
    assert (nextcloud / "Gotowe do sklepu" / source.name).is_dir()

    config.set("cloud_sync.nextcloud.local_folder", str(nextcloud))
    second = cloud_sync.archive_product(record, config)
    assert second["status"] == "ARCHIVED"
    assert not (google / "Gotowe do sklepu" / source.name).exists()
    assert not (nextcloud / "Gotowe do sklepu" / source.name).exists()


def test_folder_discovery_accepts_spaces_and_trailing_space(config, tmp_path):
    drive = tmp_path / "Mój dysk"
    root = drive / "FolderSync"
    inbox = root / "Gotowe do sklepu "
    inbox.mkdir(parents=True)
    config.set("cloud_sync.google_drive.local_folder", str(root))
    config.set("cloud_sync.google_drive.folder_name", "Folder Sync")
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")

    assert cloud_sync.discover_google_folder(config) == root
    assert cloud_sync.discover_google_inbox(config) == inbox
    assert not (root / "Gotowe do sklepu").exists()
