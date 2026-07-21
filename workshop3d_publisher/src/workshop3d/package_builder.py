"""Working copy + sales package (spec sections 5 & 13).

Originals in "Gotowe do sklepu" stay untouched. Everything happens on copies
inside the work directory:

    work/products/<product_id>/
        source/    files/    media/    listings/
        social/    package/   reports/  logs/
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

SUBDIRS = ["source", "files", "media", "listings", "social", "package", "reports", "logs"]


def workspace(work_root: Path, product_id: str) -> Path:
    base = work_root / "products" / product_id
    for sub in SUBDIRS:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def copy_sources(folder: Path, base: Path, renamed: dict[str, str]) -> dict[str, str]:
    """Copy originals into work/source (verbatim) and work/files (renamed).

    Returns a map of original-name -> renamed copy path in work/files.
    """
    source_dir = base / "source"
    files_dir = base / "files"
    result: dict[str, str] = {}
    for original in folder.rglob("*"):
        if not original.is_file():
            continue
        # Verbatim copy for archival.
        shutil.copy2(original, source_dir / original.name)
        # Renamed copy for the sales package.
        new_name = renamed.get(original.name, original.name)
        dest = files_dir / new_name
        shutil.copy2(original, dest)
        result[original.name] = str(dest)
    return result


def write_listing(base: Path, metadata: dict) -> None:
    (base / "listings" / "listing.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def write_readme_and_license(base: Path, metadata: dict, brand: str) -> None:
    lic = metadata.get("LICENSE_SUMMARY", {})
    readme = [
        f"# {metadata.get('TITLE', 'Product')}",
        "",
        metadata.get("SHORT_DESCRIPTION", ""),
        "",
        "## Included files",
    ]
    readme += [f"- {f}" for f in metadata.get("INCLUDED_FILES", [])]
    readme += ["", "## Confirmed information"]
    readme += [f"- {i}" for i in metadata.get("CONFIRMED_PRINT_INFORMATION", [])]
    readme += ["", f"(c) {brand}", "", metadata.get("DESCRIPTION_EN", "").split("\n")[-1]]
    (base / "package" / "README.txt").write_text("\n".join(readme), encoding="utf-8")

    license_text = [
        "LICENSE",
        "",
        f"Owner: {lic.get('owner', brand)}",
        f"Redistribution allowed: {lic.get('redistribution_allowed', False)}",
        f"Physical sales allowed: {lic.get('physical_sales_allowed', False)}",
        "",
        lic.get("summary", ""),
    ]
    (base / "package" / "LICENSE.txt").write_text("\n".join(license_text), encoding="utf-8")


def build_zip(base: Path, zip_name: str) -> str:
    """Bundle all files + selected media + README + LICENSE into one ZIP."""
    package_dir = base / "package"
    zip_path = package_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted((base / "files").iterdir()):
            if f.is_file():
                zf.write(f, arcname=f"files/{f.name}")
        cover = base / "media" / "cover.png"
        if cover.exists():
            zf.write(cover, arcname="cover.png")
        for extra in ("README.txt", "LICENSE.txt"):
            p = package_dir / extra
            if p.exists():
                zf.write(p, arcname=extra)
    return str(zip_path)
