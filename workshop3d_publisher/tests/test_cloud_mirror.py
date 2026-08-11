"""Non-destructive two-way mirror for finished product folders."""
import os

from workshop3d import cloud_mirror


def _configure(config, tmp_path):
    google = tmp_path / "google"
    nextcloud = tmp_path / "nextcloud"
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.local_folder", str(nextcloud))
    return google / "Gotowe do sklepu", nextcloud / "Gotowe do sklepu"


def test_new_product_folders_flow_both_ways(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    g_file = google / "Google Product" / "model.stl"
    g_file.parent.mkdir(parents=True)
    g_file.write_bytes(b"google")
    state = tmp_path / "mirror.json"

    first = cloud_mirror.sync_once(config, state)
    assert first["status"] == "SYNCED"
    assert (nextcloud / "Google Product" / "model.stl").read_bytes() == b"google"

    n_file = nextcloud / "Nextcloud Product" / "preview.png"
    n_file.parent.mkdir(parents=True)
    n_file.write_bytes(b"nextcloud")
    second = cloud_mirror.sync_once(config, state)
    assert (google / "Nextcloud Product" / "preview.png").read_bytes() == b"nextcloud"
    assert second["copied_nextcloud_to_google"] == 1

    published = nextcloud.parent / "Opublikowane" / "Old Product" / "model.stl"
    published.parent.mkdir(parents=True)
    published.write_bytes(b"published")
    cloud_mirror.sync_once(config, state)
    assert (
        google.parent / "Opublikowane" / "Old Product" / "model.stl"
    ).read_bytes() == b"published"


def test_newer_file_wins_without_conflict_duplicate(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    g_file = google / "Changed Product" / "model.stl"
    n_file = nextcloud / "Changed Product" / "model.stl"
    g_file.parent.mkdir(parents=True)
    n_file.parent.mkdir(parents=True)
    g_file.write_bytes(b"initial")
    n_file.write_bytes(b"initial")
    state = tmp_path / "mirror.json"
    cloud_mirror.sync_once(config, state)

    g_file.write_bytes(b"older edit")
    n_file.write_bytes(b"newest edit")
    os.utime(g_file, (100, 100))
    os.utime(n_file, (200, 200))
    result = cloud_mirror.sync_once(config, state)

    assert g_file.read_bytes() == n_file.read_bytes() == b"newest edit"
    assert result["conflicts"] == 1
    assert list(google.rglob("*conflict*")) == []
    assert list(nextcloud.rglob("*conflict*")) == []


def test_deletion_is_not_propagated(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    source = google / "Protected Product" / "model.stl"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"keep me")
    state = tmp_path / "mirror.json"
    cloud_mirror.sync_once(config, state)
    mirrored = nextcloud / "Protected Product" / "model.stl"
    source.unlink()

    cloud_mirror.sync_once(config, state)

    assert source.read_bytes() == mirrored.read_bytes() == b"keep me"
