"""Shared test fixtures + helpers."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

# Make the src/ package importable without installation.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workshop3d.config import Config  # noqa: E402


def make_png(path: Path, size=(64, 64)) -> None:
    """Write a small valid PNG (uses Pillow if present, else a minimal PNG)."""
    try:
        from PIL import Image
        Image.new("RGB", size, (100, 120, 140)).save(path, "PNG")
        return
    except Exception:
        pass
    # Minimal 1x1 PNG fallback.
    import zlib
    def chunk(ctype: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + ctype + data
                + struct.pack(">I", zlib.crc32(ctype + data) & 0xffffffff))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\xff\xff"
    idat = zlib.compress(raw)
    path.write_bytes(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def make_binary_stl(path: Path, triangles: int = 1) -> None:
    """Write a valid binary STL with `triangles` facets."""
    header = b"WorkShop3D test STL".ljust(80, b" ")
    body = struct.pack("<I", triangles)
    for _ in range(triangles):
        # normal (3f) + 3 vertices (9f) + attribute byte count (H)
        body += struct.pack("<12fH", *([0.0] * 12), 0)
    path.write_bytes(header + body)


def make_glb(path: Path) -> None:
    path.write_bytes(b"glTF" + struct.pack("<II", 2, 20) + b"\x00" * 12)


def make_3mf(path: Path) -> None:
    # 3MF is a zip container; a minimal placeholder is fine for detection tests.
    import zipfile
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("3D/3dmodel.model", "<model/>")


@pytest.fixture
def product_folder(tmp_path):
    """Factory: create a product folder with chosen files."""
    def _make(name="Dark Fantasy Dungeon Door", png=True, stl=True, glb=False, tmf=False,
              extra_png=0, extra_stl=0, root=None):
        root = root or (tmp_path / "ready")
        folder = root / name
        folder.mkdir(parents=True, exist_ok=True)
        if png:
            make_png(folder / f"{name}.png")
        for i in range(extra_png):
            make_png(folder / f"{name}_extra{i}.png")
        if stl:
            make_binary_stl(folder / f"{name}.stl")
        for i in range(extra_stl):
            make_binary_stl(folder / f"{name}_part{i}.stl", triangles=2)
        if glb:
            make_glb(folder / f"{name}.glb")
        if tmf:
            make_3mf(folder / f"{name}.3mf")
        return folder
    return _make


@pytest.fixture
def config(tmp_path):
    """Config pointing paths into tmp_path, DRY_RUN on, Cults3D+Thangs enabled."""
    data = {
        "paths": {"ready_folder": str(tmp_path / "ready"), "work_folder": str(tmp_path / "work")},
        "modes": {"dry_run": True, "auto_publish": False},
        "trigger": {"stability_delay_seconds": 0, "stability_checks": 2,
                    "seconds_between_checks": 0,
                    "ignore_patterns": ["*.tmp", "*.part", "*.crdownload"]},
        "retry": {"max_attempts": 3, "backoff_seconds": [1, 2, 4]},
        "brand": {"name": "WorkShop3D", "signature": "Regards.\nRafal z WorkShop3D",
                  "collections": [
                      {"id": "kroniki_fallathanu", "display_name": "Kroniki Fallathanu",
                       "match_keywords": ["fallathan"], "tags": ["kroniki fallathanu", "dark fantasy"]}
                  ]},
        "pricing": {"currency": "USD", "single_model": 4.99, "bundle_small": 13.99, "free_products": False},
        "licensing": {"default": {"redistribution_allowed": False, "physical_sales_allowed": False,
                                  "owner": "WorkShop3D", "summary": "No redistribution."}},
        "categories": {"default": "miniature", "keyword_map": {"door": "terrain", "bundle": "bundle"}},
        "stores": {"cults3d": {"enabled": True, "mode": "api", "publish_as": "draft"},
                   "thangs": {"enabled": True, "mode": "api", "publish_as": "draft"}},
        "social": {"facebook": {"enabled": True, "language": "pl"}},
        "links": {"main_link_priority": ["cults3d", "thangs"]},
    }
    return Config(data)
