"""Google FolderSync is a safe, persistent publishing inbox."""
from workshop3d.cloud_inbox import CloudInboxWatcher


def test_existing_folders_are_baselined_then_new_and_changed_are_processed(
    product_folder, config, tmp_path
):
    google = tmp_path / "google"
    inbox = google / "Gotowe do sklepu"
    old = product_folder(name="Historical Product", root=inbox)
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("trigger.stability_delay_seconds", 0)
    config.set("trigger.stability_checks", 1)
    handed_over = []
    watcher = CloudInboxWatcher(
        config,
        handed_over.append,
        state_path=tmp_path / "inbox-state.json",
    )

    watcher.poll_once(now=lambda: 10.0)
    assert handed_over == []

    new = product_folder(name="New Product", root=inbox)
    watcher.poll_once(now=lambda: 20.0)  # first observation
    watcher.poll_once(now=lambda: 21.0)  # unchanged and stable
    assert handed_over == [new]

    (old / "extra.txt").write_text("changed", encoding="utf-8")
    watcher.poll_once(now=lambda: 30.0)
    watcher.poll_once(now=lambda: 31.0)
    assert handed_over == [new, old]


def test_loose_files_are_not_products(config, tmp_path):
    google = tmp_path / "google"
    inbox = google / "Gotowe do sklepu"
    inbox.mkdir(parents=True)
    (inbox / "readme.txt").write_text("not a product")
    config.set("cloud_sync.google_drive.local_folder", str(google))
    config.set("cloud_sync.inbox_folder", "Gotowe do sklepu")
    called = []
    watcher = CloudInboxWatcher(
        config, called.append, state_path=tmp_path / "inbox-state.json"
    )

    watcher.poll_once(now=lambda: 1.0)
    watcher.poll_once(now=lambda: 2.0)

    assert called == []
