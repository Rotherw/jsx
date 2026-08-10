"""Product graphics (spec section 12).

Uses the delivered PNG as the real product presentation. Never alters the
model's geometry or appearance -- only composes marketing frames (cover,
thumbnail, social sizes) around the supplied image. Only lists formats that
actually exist in the folder.
"""
from __future__ import annotations

import shutil
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    _HAVE_PIL = True
except Exception:  # pragma: no cover
    _HAVE_PIL = False

# Target frames: name -> (width, height).
FRAMES = {
    "cover": (1200, 900),
    "thumbnail_thangs": (600, 600),
    "cults3d": (1000, 1000),
    "social_vertical": (1080, 1350),
    "social_square": (1080, 1080),
}


def _fit(im, size):
    """Contain the image on a dark canvas of the target size (no distortion)."""
    canvas = Image.new("RGB", size, (18, 18, 22))
    src = im.convert("RGB")
    src.thumbnail((size[0], int(size[1] * 0.82)), Image.LANCZOS)
    x = (size[0] - src.width) // 2
    y = (size[1] - src.height) // 2 - int(size[1] * 0.05)
    canvas.paste(src, (x, y))
    return canvas


def _caption(canvas, title, brand, formats, collection):
    draw = ImageDraw.Draw(canvas)
    try:
        font_big = ImageFont.truetype("arial.ttf", 42)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    w, h = canvas.size
    draw.text((30, h - 90), title, fill=(240, 240, 245), font=font_big)
    line2 = brand
    if collection:
        line2 += f"  |  {collection}"
    line2 += f"  |  {' / '.join(formats)}"
    draw.text((30, h - 42), line2, fill=(180, 180, 190), font=font_small)
    return canvas


def render(
    main_png: Path,
    media_dir: Path,
    title: str,
    brand: str,
    formats: list[str],
    collection: str | None = None,
) -> list[str]:
    """Generate marketing frames. Returns list of created file paths (str)."""
    media_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    if not _HAVE_PIL:
        # Fallback: copy the original PNG as the cover so the pipeline still runs.
        dest = media_dir / "cover.png"
        shutil.copy2(main_png, dest)
        return [str(dest)]

    with Image.open(main_png) as im:
        im.load()
        for frame_name, size in FRAMES.items():
            canvas = _fit(im, size)
            canvas = _caption(canvas, title, brand, formats, collection)
            out = media_dir / f"{frame_name}.png"
            canvas.save(out, "PNG")
            created.append(str(out))
    return created
