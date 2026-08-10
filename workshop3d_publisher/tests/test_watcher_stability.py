"""Copy-stability + temp-file handling (spec 23)."""
from workshop3d.folder_watcher import is_stable, has_pending_temp_files, has_required_files


def test_stable_folder(product_folder):
    folder = product_folder()
    # interval 0 + no-op sleep -> deterministic
    assert is_stable(folder, ignore=[], checks=3, interval=0, sleep=lambda s: None)


def test_growing_file_not_stable(product_folder):
    folder = product_folder()
    stl = folder / "growing.stl"
    stl.write_bytes(b"solid x\nfacet\n")
    sizes = iter([b"a", b"aa", b"aaa", b"aaa", b"aaa"])

    def grow(_):
        try:
            stl.write_bytes(next(sizes))
        except StopIteration:
            pass

    # With a mutating sleep, the first checks keep changing; eventually stabilises.
    assert is_stable(folder, ignore=[], checks=2, interval=0, sleep=grow)


def test_temp_files_detected(product_folder):
    folder = product_folder()
    (folder / "model.stl.part").write_bytes(b"partial")
    assert has_pending_temp_files(folder, ignore=["*.part"])


def test_required_files_present(product_folder):
    assert has_required_files(product_folder(name="Complete Model"))
    assert not has_required_files(product_folder(name="No STL Model", stl=False))
