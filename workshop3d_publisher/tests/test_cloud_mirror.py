"""Non-destructive mirror for finished product folders.

Two contracts are covered: the default one-way push (Google Folder Sync is the
working area, Nextcloud Folder Sync is the post-sale archive) and the older
two-way mirror, which is still selectable via ``cloud_sync.mirror_direction``.
"""
import os

from workshop3d import cloud_mirror


def _configure(config, tmp_path, direction=None, folder="Opublikowane"):
    """Zwraca pare folderow ``folder`` po obu stronach.

    Jednostronnie lustro pilnuje wylacznie ``Opublikowane``, dlatego to on jest
    domyslnym punktem odniesienia. Testy dwustronne podaja skrzynke wejsciowa.
    """
    google = tmp_path / "google"
    nextcloud = tmp_path / "nextcloud"
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.published_folder", "Opublikowane")
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.nextcloud.local_folder", str(nextcloud))
    if direction is not None:
        config.set("cloud_sync.mirror_direction", direction)
    return google / folder, nextcloud / folder


# --------------------------------------------------------------- jednostronnie

def test_one_way_is_the_default(config, tmp_path):
    _configure(config, tmp_path)

    assert cloud_mirror.direction(config) == cloud_mirror.DIRECTION_ONE_WAY


def test_working_area_is_pushed_to_the_archive(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    source = google / "Castle Doflot" / "model.stl"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"google")
    state = tmp_path / "mirror.json"

    result = cloud_mirror.sync_once(config, state)

    assert result["status"] == "SYNCED"
    assert result["direction"] == cloud_mirror.DIRECTION_ONE_WAY
    assert (nextcloud / "Castle Doflot" / "model.stl").read_bytes() == b"google"
    assert result["copied_google_to_nextcloud"] == 1
    assert result["copied_nextcloud_to_google"] == 0


def test_archive_only_file_is_never_pulled_back(config, tmp_path):
    """Sprzatniecie opublikowanej paczki z obszaru roboczego ma zostac sprzatnieciem."""
    google, nextcloud = _configure(config, tmp_path)
    archived = nextcloud / "Sold Product" / "model.stl"
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"sold")
    google.mkdir(parents=True)
    state = tmp_path / "mirror.json"

    result = cloud_mirror.sync_once(config, state)

    assert not (google / "Sold Product").exists()
    assert archived.read_bytes() == b"sold"
    assert result["copied_nextcloud_to_google"] == 0


def test_cleared_working_copy_is_not_restored_by_the_archive(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    source = google / "Published Product" / "model.stl"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"keep me")
    state = tmp_path / "mirror.json"
    cloud_mirror.sync_once(config, state)
    mirrored = nextcloud / "Published Product" / "model.stl"
    assert mirrored.read_bytes() == b"keep me"

    source.unlink()
    cloud_mirror.sync_once(config, state)

    assert not source.exists()
    assert mirrored.read_bytes() == b"keep me"


def test_working_copy_wins_over_archive_edit(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path)
    g_file = google / "Changed Product" / "model.stl"
    n_file = nextcloud / "Changed Product" / "model.stl"
    g_file.parent.mkdir(parents=True)
    n_file.parent.mkdir(parents=True)
    g_file.write_bytes(b"initial")
    n_file.write_bytes(b"initial")
    state = tmp_path / "mirror.json"
    cloud_mirror.sync_once(config, state)

    # Nawet gdy kopia w archiwum jest nowsza, zrodlem prawdy jest obszar roboczy.
    g_file.write_bytes(b"working copy")
    n_file.write_bytes(b"archive edit")
    os.utime(g_file, (100, 100))
    os.utime(n_file, (200, 200))
    result = cloud_mirror.sync_once(config, state)

    assert g_file.read_bytes() == n_file.read_bytes() == b"working copy"
    assert result["copied_nextcloud_to_google"] == 0
    assert list(google.rglob("*conflict*")) == []
    assert list(nextcloud.rglob("*conflict*")) == []


# ------------------------------------------------------------------ dwustronnie

def test_two_way_flows_both_directions(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path, cloud_mirror.DIRECTION_TWO_WAY, "Gotowe do sklepu")
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


def test_two_way_newer_file_wins_without_conflict_duplicate(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path, cloud_mirror.DIRECTION_TWO_WAY, "Gotowe do sklepu")
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


def test_two_way_deletion_is_not_propagated(config, tmp_path):
    google, nextcloud = _configure(config, tmp_path, cloud_mirror.DIRECTION_TWO_WAY, "Gotowe do sklepu")
    source = google / "Protected Product" / "model.stl"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"keep me")
    state = tmp_path / "mirror.json"
    cloud_mirror.sync_once(config, state)
    mirrored = nextcloud / "Protected Product" / "model.stl"
    source.unlink()

    cloud_mirror.sync_once(config, state)

    assert source.read_bytes() == mirrored.read_bytes() == b"keep me"


def test_inbox_is_not_pushed_to_the_archive(config, tmp_path):
    """Praca w toku zostaje na Google; magazyn dostaje tylko Opublikowane."""
    google, nextcloud = _configure(config, tmp_path)
    in_progress = google.parent / "Gotowe do sklepu" / "Work In Progress" / "model.stl"
    in_progress.parent.mkdir(parents=True)
    in_progress.write_bytes(b"not ready yet")
    done = google / "Finished Product" / "model.stl"
    done.parent.mkdir(parents=True)
    done.write_bytes(b"ready")

    result = cloud_mirror.sync_once(config, tmp_path / "mirror.json")

    assert cloud_mirror.mirrored_folders(config) == {"Opublikowane"}
    assert not (nextcloud.parent / "Gotowe do sklepu").exists()
    assert (nextcloud / "Finished Product" / "model.stl").read_bytes() == b"ready"
    assert result["copied_google_to_nextcloud"] == 1
