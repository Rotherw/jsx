"""Product fact card (spec section 6).

Splits information into CONFIRMED / SAFE_INFERENCES / UNKNOWN and refuses to
invent anything (scale, dimensions, print settings, lore, game-compatibility,
third-party licences, part counts not derivable from files, ...).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Config
from .file_validator import ValidationResult

# Product-type keyword recognition -> a *safe inference*, never a hard claim.
_TYPE_KEYWORDS = {
    "terrain": ["terrain", "dungeon", "door", "wall", "floor", "building", "house", "tower", "bridge"],
    "building": ["building", "house", "tower", "castle", "keep"],
    "miniature": ["miniature", "mini", "npc", "hero", "warrior", "knight", "monster", "figure", "character"],
    "prop": ["prop", "chest", "barrel", "crate", "torch", "banner", "shield", "weapon"],
    "diorama": ["diorama", "scene", "base"],
    "bundle": ["bundle", "pack", "set", "collection"],
}


def _detect_type(name: str, stl_count: int) -> tuple[str, str]:
    """Return (product_type, reason). Safe inference only."""
    low = name.lower()
    for ptype, kws in _TYPE_KEYWORDS.items():
        for kw in kws:
            if kw in low:
                return ptype, f'folder name contains "{kw}"'
    if stl_count >= 3:
        return "bundle", f"{stl_count} STL files present"
    return "unknown", "no reliable signal in folder name"


def build_fact_card(
    folder: Path,
    validation: ValidationResult,
    config: Config,
) -> dict[str, Any]:
    name = folder.name
    stl_count = len(validation.stl_files)
    ptype, reason = _detect_type(name, stl_count)

    confirmed: list[str] = [
        f"Working product name (folder): {name}",
        f"STL files delivered: {stl_count}",
        f"PNG images delivered: {len(validation.png_files)}",
    ]
    if validation.glb_files:
        confirmed.append(f"GLB files delivered: {len(validation.glb_files)}")
    if validation.tmf_files:
        confirmed.append(f"3MF files delivered: {len(validation.tmf_files)}")

    safe_inferences: list[str] = [
        f"Product type: {ptype} ({reason})",
    ]
    if stl_count >= 3:
        safe_inferences.append("Likely a multi-part product or bundle")

    # Deliberately-unknown fields we must NOT invent.
    unknown = [
        "scale", "dimensions in mm", "test print performed", "print time",
        "filament usage", "material type", "layer height", "nozzle size",
        "supports required", "resin/FDM readiness", "game compatibility",
        "third-party licence / lore",
    ]

    # Collection detection (folder name / configured rules only).
    collection = _detect_collection(name, config)

    return {
        "product_type": ptype,
        "collection": collection,          # None if not recognised -> WorkShop3D only
        "confirmed": confirmed,
        "safe_inferences": safe_inferences,
        "unknown": unknown,
    }


def _detect_collection(name: str, config: Config) -> dict | None:
    low = name.lower()
    for coll in config.get("brand.collections", []) or []:
        for kw in coll.get("match_keywords", []):
            if kw.lower() in low:
                return {
                    "id": coll.get("id"),
                    "display_name": coll.get("display_name"),
                    "tags": coll.get("tags", []),
                }
    return None
