"""Validation + detection tests (spec 23: complete folder, missing PNG/STL,
extra GLB/3MF, multiple STL/PNG)."""
from workshop3d.file_validator import validate


def test_complete_folder_is_valid(product_folder):
    folder = product_folder()
    res = validate(folder)
    assert res.ok
    assert res.png_files and res.stl_files
    assert res.checksums


def test_missing_png_detected(product_folder):
    folder = product_folder(png=False)
    res = validate(folder)
    assert not res.ok
    assert any("PNG" in e for e in res.errors)


def test_missing_stl_detected(product_folder):
    folder = product_folder(stl=False)
    res = validate(folder)
    assert not res.ok
    assert any("STL" in e for e in res.errors)


def test_extra_glb_recognised(product_folder):
    folder = product_folder(glb=True)
    res = validate(folder)
    assert res.ok
    assert len(res.glb_files) == 1


def test_extra_3mf_recognised(product_folder):
    folder = product_folder(tmf=True)
    res = validate(folder)
    assert res.ok
    assert len(res.tmf_files) == 1


def test_multiple_stl(product_folder):
    folder = product_folder(extra_stl=2)
    res = validate(folder)
    assert res.ok
    assert len(res.stl_files) == 3


def test_multiple_png(product_folder):
    folder = product_folder(extra_png=2)
    res = validate(folder)
    assert res.ok
    assert len(res.png_files) == 3


def test_corrupt_png_flagged(product_folder):
    folder = product_folder()
    (folder / "broken.png").write_bytes(b"not really a png")
    res = validate(folder)
    assert not res.ok
    assert any("PNG" in e for e in res.errors)


def test_empty_stl_flagged(product_folder):
    folder = product_folder()
    (folder / "empty.stl").write_bytes(b"")
    res = validate(folder)
    assert not res.ok
