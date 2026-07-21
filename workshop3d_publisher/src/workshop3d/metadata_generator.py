"""Metadata generation (spec sections 7, 9, 10, 11).

Produces titles, slug, descriptions (EN + PL), included-files list, confirmed
print info, licence summary, tags, category, price, per-platform settings and
social texts. Everything is derived ONLY from confirmed data + configuration --
no invented technical specs, scale, lore or game compatibility.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Config
from .file_validator import ValidationResult
from . import text_utils as tu


def _category(name: str, fact_card: dict, config: Config) -> str:
    low = name.lower()
    for kw, cat in (config.get("categories.keyword_map", {}) or {}).items():
        if kw.lower() in low:
            return cat
    # Fall back to the analyzer's product type, then configured default.
    ptype = fact_card.get("product_type")
    if ptype and ptype != "unknown":
        return ptype
    return config.get("categories.default", "miniature")


def _price(fact_card: dict, config: Config) -> dict:
    is_bundle = fact_card.get("product_type") == "bundle"
    amount = (
        config.get("pricing.bundle_small", 13.99)
        if is_bundle
        else config.get("pricing.single_model", 4.99)
    )
    if config.get("pricing.free_products", False):
        amount = 0.0
    return {"amount": round(float(amount), 2), "currency": config.get("pricing.currency", "USD")}


def _tags(name: str, fact_card: dict, config: Config, limit: int = 20) -> list[str]:
    """Content-driven tags. Up to 15 product tags + 5 brand/series tags."""
    ptype = fact_card.get("product_type", "unknown")
    product_tags: list[str] = []

    def add(t: str) -> None:
        t = t.strip().lower()
        if t and t not in product_tags:
            product_tags.append(t)

    # Derive from the folder name words.
    for word in tu.title_case(name).split():
        if len(word) >= 3:
            add(word.lower())

    # Type-specific intent tags.
    type_intent = {
        "terrain": ["terrain", "tabletop terrain", "dnd terrain", "rpg terrain", "scatter terrain", "dungeon"],
        "building": ["building", "fantasy building", "tabletop", "rpg", "scenery"],
        "miniature": ["miniature", "tabletop miniature", "dnd miniature", "rpg miniature", "npc", "fantasy"],
        "prop": ["prop", "tabletop prop", "rpg prop", "fantasy prop", "accessory"],
        "diorama": ["diorama", "display", "collectible", "fantasy", "scene"],
        "bundle": ["bundle", "model pack", "value pack", "tabletop set", "collection"],
        "unknown": ["3d model", "3d printable", "stl", "tabletop", "fantasy"],
    }
    for t in type_intent.get(ptype, type_intent["unknown"]):
        add(t)

    # Generic buying-intent tags, then a padding pool so we can reach 15.
    for t in ["3d print", "stl file", "3d printable", "dnd", "wargaming", "miniatures",
              "tabletop gaming", "hobby", "collectible", "model kit", "scenery",
              "print at home", "rpg", "fantasy", "3d model"]:
        add(t)

    product_count = min(15, limit - 1)  # leave room for >=1 brand tag
    product_tags = product_tags[:product_count]

    # Brand / series tags (target up to 5), padded from a brand pool.
    brand_tags: list[str] = []

    def add_brand(t: str) -> None:
        t = t.strip().lower()
        if t and t not in brand_tags and t not in product_tags:
            brand_tags.append(t)

    add_brand(config.get("brand.name", "WorkShop3D"))
    coll = fact_card.get("collection")
    if coll:
        for t in coll.get("tags", []):
            add_brand(t)
        if coll.get("display_name"):
            add_brand(coll["display_name"])
    for t in ["3d printing", "tabletop gaming", "fantasy", "stl files", "3d models"]:
        add_brand(t)

    brand_count = min(5, limit - len(product_tags))
    brand_tags = brand_tags[:brand_count]

    return (product_tags + brand_tags)[:limit]


def _confirmed_print_info(validation: ValidationResult) -> list[str]:
    """ONLY facts we can confirm from the delivered files."""
    formats = ["STL"]
    if validation.glb_files:
        formats.append("GLB")
    if validation.tmf_files:
        formats.append("3MF")
    info = [f"Provided file formats: {', '.join(formats)}"]
    info.append(f"Number of STL files: {len(validation.stl_files)}")
    # No scale, no supports claim, no material, no print time -- unconfirmed.
    return info


def _description_en(title: str, fact_card: dict, included: list[str],
                    print_info: list[str], brand: str, coll: dict | None,
                    signature: str) -> str:
    ptype = fact_card.get("product_type", "model")
    lines = [
        f"{title} - a 3D printable {ptype} from {brand}.",
        "",
        f"This is a finished {ptype} product ready to download and 3D print.",
        "Great for tabletop RPGs, wargaming and hobby display, depending on your setup.",
        "",
        "Included files:",
    ]
    lines += [f"  - {f}" for f in included]
    lines += ["", "Confirmed information:"]
    lines += [f"  - {i}" for i in print_info]
    if coll:
        lines += ["", f"Part of the {coll['display_name']} collection by {brand}."]
    else:
        lines += ["", f"A {brand} release."]
    lines += ["", signature.strip()]
    return "\n".join(lines)


def _description_pl(title: str, fact_card: dict, included: list[str],
                    brand: str, coll: dict | None, signature: str) -> str:
    ptype = fact_card.get("product_type", "model")
    lines = [
        f"{title} - model 3D do druku od {brand}.",
        "",
        f"Gotowy produkt typu {ptype}, gotowy do pobrania i wydruku 3D.",
        "",
        "Dostarczone pliki:",
    ]
    lines += [f"  - {f}" for f in included]
    if coll:
        lines += ["", f"Czesc kolekcji {coll['display_name']} od {brand}."]
    lines += ["", signature.strip()]
    return "\n".join(lines)


def _social_texts(title: str, ptype: str, coll: dict | None) -> dict:
    coll_tag = ""
    if coll:
        coll_tag = " #" + tu.file_token(coll["display_name"]).lower()
    base_tags = f"#workshop3d #3dprinting #{ptype} #dnd #tabletop{coll_tag}"
    return {
        "facebook": {
            "text": f"Nowy model dostepny: {title}! Sprawdz w naszym sklepie.",
            "hashtags": base_tags,
        },
        "instagram": {
            "text": f"{title} - new from WorkShop3D. Check it out!",
            "hashtags": base_tags + " #3dprint #miniatures",
        },
        "tiktok": {
            "text": f"{title} - now available. Link in profile.",
            "hashtags": base_tags,
        },
        "youtube": {
            "text": f"{title} by WorkShop3D is now available.",
            "hashtags": base_tags,
        },
    }


def generate(
    folder: Path,
    validation: ValidationResult,
    fact_card: dict,
    config: Config,
) -> dict[str, Any]:
    brand = config.get("brand.name", "WorkShop3D")
    signature = config.get("brand.signature", "Regards.\nRafal z WorkShop3D")
    coll = fact_card.get("collection")

    raw_name = tu.title_case(folder.name)
    title = raw_name
    # Ensure no file extensions leak into the title.
    for ext in (".stl", ".glb", ".3mf", ".png"):
        title = title.replace(ext, "").replace(ext.upper(), "")
    title = title.strip()

    short_title = title if len(title) <= 60 else title[:57].rstrip() + "..."
    slug = tu.slugify(f"{brand}-{title}")

    included = list(validation.stl_files)
    included += list(validation.tmf_files)
    included += list(validation.glb_files)
    included += list(validation.png_files)

    category = _category(folder.name, fact_card, config)
    price = _price(fact_card, config)
    print_info = _confirmed_print_info(validation)
    tags = _tags(folder.name, fact_card, config)

    # Normalised copy file names (originals are never renamed).
    token = tu.file_token(f"{brand}_{title}")
    renamed: dict[str, str] = {}
    for i, stl in enumerate(validation.stl_files, 1):
        suffix = f"_{i}" if len(validation.stl_files) > 1 else ""
        renamed[stl] = f"{token}{suffix}.stl"
    for i, png in enumerate(validation.png_files, 1):
        suffix = f"_{i}" if len(validation.png_files) > 1 else ""
        renamed[png] = f"{token}{suffix}.png"
    for ext, files in (("glb", validation.glb_files), ("3mf", validation.tmf_files)):
        for i, f in enumerate(files, 1):
            suffix = f"_{i}" if len(files) > 1 else ""
            renamed[f] = f"{token}{suffix}.{ext}"

    zip_name = f"{token}.zip"

    licence = _license_summary(config)

    return {
        "TITLE": title,
        "SHORT_TITLE": short_title,
        "TITLE_PL": title,
        "SLUG": slug,
        "SHORT_DESCRIPTION": f"{title} - 3D printable {fact_card.get('product_type','model')} by {brand}.",
        "DESCRIPTION_EN": _description_en(title, fact_card, included, print_info, brand, coll, signature),
        "DESCRIPTION_PL": _description_pl(title, fact_card, included, brand, coll, signature),
        "INCLUDED_FILES": included,
        "CONFIRMED_PRINT_INFORMATION": print_info,
        "LICENSE_SUMMARY": licence,
        "TAGS": tags,
        "CATEGORY": category,
        "PRICE": price,
        "PLATFORM_SETTINGS": {},   # filled per adapter at publish time
        "SOCIAL_MEDIA_TEXTS": _social_texts(title, fact_card.get("product_type", "model"), coll),
        "RENAMED_FILES": renamed,
        "ZIP_NAME": zip_name,
    }


def _license_summary(config: Config) -> dict:
    default = config.get("licensing.default", {}) or {}
    return {
        "redistribution_allowed": default.get("redistribution_allowed", False),
        "physical_sales_allowed": default.get("physical_sales_allowed", False),
        "owner": default.get("owner", "WorkShop3D"),
        "summary": default.get(
            "summary",
            "Digital files may not be redistributed. All rights remain with WorkShop3D.",
        ),
    }
