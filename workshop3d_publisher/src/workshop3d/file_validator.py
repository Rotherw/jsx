"""File validation and checksums (spec section 5).

Never modifies, deletes or moves the original files. Only reads them.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

try:  # Pillow is a hard dependency, but keep validation working if absent.
    from PIL import Image  # type: ignore
    _HAVE_PIL = True
except Exception:  # pragma: no cover
    _HAVE_PIL = False


@dataclass
class ValidationResult:
    ok: bool
    png_files: list[str] = field(default_factory=list)
    stl_files: list[str] = field(default_factory=list)
    glb_files: list[str] = field(default_factory=list)
    tmf_files: list[str] = field(default_factory=list)
    checksums: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_png(path: Path) -> bool:
    """Check the PNG is readable and not corrupt."""
    try:
        # PNG 8-byte magic number.
        with open(path, "rb") as fh:
            if fh.read(8) != b"\x89PNG\r\n\x1a\n":
                return False
        if _HAVE_PIL:
            with Image.open(path) as im:
                im.verify()
        return True
    except Exception:
        return False


def stl_has_data(path: Path) -> bool:
    """Confirm an STL actually contains geometry (binary or ASCII)."""
    try:
        size = path.stat().st_size
        if size < 15:
            return False
        with open(path, "rb") as fh:
            head = fh.read(512)
        # ASCII STL starts with "solid" and contains facet/vertex keywords.
        if head[:5].lower() == b"solid" and (b"facet" in head or b"vertex" in head):
            return True
        # Binary STL: 80-byte header + 4-byte little-endian triangle count.
        if size >= 84:
            with open(path, "rb") as fh:
                fh.seek(80)
                (count,) = struct.unpack("<I", fh.read(4))
            expected = 84 + count * 50
            # Allow trailing bytes but require the count to be plausible & > 0.
            if count > 0 and size >= expected:
                return True
        # ASCII STL whose header keywords sit beyond first 512 bytes.
        if head[:5].lower() == b"solid":
            return True
        return False
    except Exception:
        return False


def classify(folder: Path) -> dict[str, list[Path]]:
    """Group product files by extension (recursively within the folder)."""
    buckets: dict[str, list[Path]] = {"png": [], "stl": [], "glb": [], "3mf": []}
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower().lstrip(".")
        if ext in buckets:
            buckets[ext].append(p)
    return buckets


def validate(folder: Path) -> ValidationResult:
    """Validate a product folder. Returns ok=False with reasons if incomplete."""
    res = ValidationResult(ok=True)

    if not folder.name.strip():
        res.ok = False
        res.errors.append("Empty folder name.")
        return res

    buckets = classify(folder)

    # Required: at least one PNG and one STL.
    if not buckets["png"]:
        res.ok = False
        res.errors.append("Missing required PNG file.")
    if not buckets["stl"]:
        res.ok = False
        res.errors.append("Missing required STL file.")

    # Validate PNGs.
    for png in buckets["png"]:
        if is_valid_png(png):
            res.png_files.append(png.name)
        else:
            res.ok = False
            res.errors.append(f"Unreadable/corrupt PNG: {png.name}")

    # Validate STLs.
    for stl in buckets["stl"]:
        if stl_has_data(stl):
            res.stl_files.append(stl.name)
        else:
            res.ok = False
            res.errors.append(f"STL contains no data: {stl.name}")

    res.glb_files = [p.name for p in buckets["glb"]]
    res.tmf_files = [p.name for p in buckets["3mf"]]

    # Checksums over every product file (identity + dedup key).
    for group in buckets.values():
        for p in group:
            try:
                res.checksums[p.name] = sha256(p)
            except OSError as exc:
                res.ok = False
                res.errors.append(f"Cannot read {p.name}: {exc}")

    return res
