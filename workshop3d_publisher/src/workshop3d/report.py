"""Final report generation (spec section 18): publication_report.json + .md."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .models import ProductRecord


def _completion_date() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def build_report(record: ProductRecord, reports_dir: Path) -> tuple[str, str]:
    reports_dir.mkdir(parents=True, exist_ok=True)

    published_stores = [p for p, r in record.stores.items()
                        if r.get("status") in ("PUBLISHED", "DRY_RUN")]
    store_links = {p: r.get("url") for p, r in record.stores.items() if r.get("url")}
    social_posts = [p for p, r in record.social.items()
                    if r.get("status") in ("POSTED", "DRY_RUN")]
    social_links = {p: r.get("post_url") for p, r in record.social.items() if r.get("post_url")}
    failed_steps = [f"{p}: {r.get('message')}" for p, r in {**record.stores, **record.social}.items()
                    if r.get("status") in ("FAILED", "NOT_CONNECTED", "NEEDS_ATTENTION")]

    data = {
        "PRODUCT": record.metadata.get("TITLE", record.folder_name),
        "STATUS": record.state,
        "DETECTED_FILES": {
            "png": record.png_files,
            "stl": record.stl_files,
            "glb": record.glb_files,
            "3mf": record.tmf_files,
        },
        "GENERATED_MATERIALS": record.media,
        "PUBLISHED_STORES": published_stores,
        "STORE_LINKS": store_links,
        "SOCIAL_POSTS": social_posts,
        "SOCIAL_LINKS": social_links,
        "FAILED_STEPS": failed_steps,
        "REQUIRED_USER_ACTION": record.required_user_action,
        "COMPLETION_DATE": _completion_date(),
    }

    json_path = reports_dir / "publication_report.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [f"# Publication report: {data['PRODUCT']}", ""]
    for key in ["STATUS", "COMPLETION_DATE", "REQUIRED_USER_ACTION"]:
        md_lines.append(f"**{key}:** {data[key]}")
    md_lines += ["", "## Detected files"]
    for kind, files in data["DETECTED_FILES"].items():
        if files:
            md_lines.append(f"- {kind.upper()}: {', '.join(files)}")
    md_lines += ["", "## Published stores"]
    md_lines += [f"- {p}: {store_links.get(p, 'n/a')}" for p in published_stores] or ["- none"]
    md_lines += ["", "## Social posts"]
    md_lines += [f"- {p}: {social_links.get(p, 'prepared')}" for p in social_posts] or ["- none"]
    if failed_steps:
        md_lines += ["", "## Failed / needs attention"]
        md_lines += [f"- {s}" for s in failed_steps]

    md_path = reports_dir / "publication_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return str(json_path), str(md_path)
