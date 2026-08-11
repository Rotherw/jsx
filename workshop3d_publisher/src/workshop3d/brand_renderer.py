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


def _font(path: Path | None, size: int):
    candidates = [path, Path("C:/Windows/Fonts/segoeui.ttf"), Path("arial.ttf")]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return ImageFont.truetype(str(candidate), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_title(draw, title: str, font, max_width: int, max_lines: int = 2) -> list[str]:
    words = title.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
        else:
            current = candidate
    if current and len(lines) < max_lines:
        remaining = " ".join(words[len(" ".join(lines + [current]).split()):])
        if remaining:
            current = f"{current} {remaining}"
        while draw.textbbox((0, 0), current, font=font)[2] > max_width and len(current) > 4:
            current = current[:-2].rstrip() + "…"
        lines.append(current)
    return lines or [title]


def _paste_logo(canvas, path: Path | None, box: tuple[int, int], position: tuple[int, int]) -> bool:
    if path is None or not path.is_file():
        return False
    try:
        with Image.open(path) as raw:
            logo = raw.convert("RGBA")
            logo.thumbnail(box, Image.LANCZOS)
            canvas.paste(logo, position, logo)
        return True
    except Exception:
        return False


def _caption(
    canvas,
    title,
    brand,
    formats,
    collection,
    font_path: Path | None,
    logo_path: Path | None,
    patron_name: str,
    patron_logo_path: Path | None,
):
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    scale = max(0.55, w / 1200)
    font_big = _font(font_path, max(22, int(48 * scale)))
    font_small = _font(None, max(14, int(24 * scale)))
    font_brand = _font(font_path, max(18, int(30 * scale)))

    # WorkShop3D and KF2.pl remain visually separate: maker at top-left,
    # patron at top-right. Missing user logos fall back to honest text labels.
    margin = max(18, int(30 * scale))
    logo_box = (max(90, int(230 * scale)), max(46, int(95 * scale)))
    if not _paste_logo(canvas, logo_path, logo_box, (margin, margin)):
        draw.text((margin, margin), brand, fill=(248, 210, 100), font=font_brand)

    patron_label = f"Patron: {patron_name}" if patron_name else ""
    patron_width = draw.textbbox((0, 0), patron_label, font=font_small)[2] if patron_label else 0
    patron_x = max(margin, w - margin - max(logo_box[0], patron_width))
    if not _paste_logo(canvas, patron_logo_path, logo_box, (patron_x, margin)) and patron_label:
        draw.text((w - margin - patron_width, margin), patron_label,
                  fill=(190, 190, 200), font=font_small)

    footer_height = max(110, int(h * 0.18))
    draw.rectangle((0, h - footer_height, w, h), fill=(12, 12, 16))
    title_lines = _wrap_title(draw, title, font_big, w - 2 * margin)
    line_height = draw.textbbox((0, 0), "Ag", font=font_big)[3] + max(2, int(4 * scale))
    y = h - footer_height + max(10, int(16 * scale))
    for line in title_lines:
        draw.text((margin, y), line, fill=(245, 245, 248), font=font_big)
        y += line_height

    line2 = brand
    if collection:
        line2 += f"  |  {collection}"
    line2 += f"  |  {' / '.join(formats)}"
    draw.text((margin, h - margin - max(16, int(18 * scale))), line2,
              fill=(180, 180, 190), font=font_small)
    return canvas


def render(
    main_png: Path,
    media_dir: Path,
    title: str,
    brand: str,
    formats: list[str],
    collection: str | None = None,
    font_path: Path | None = None,
    logo_path: Path | None = None,
    patron_name: str = "KF2.pl",
    patron_logo_path: Path | None = None,
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
            canvas = _caption(
                canvas, title, brand, formats, collection,
                font_path, logo_path, patron_name, patron_logo_path,
            )
            out = media_dir / f"{frame_name}.png"
            canvas.save(out, "PNG")
            created.append(str(out))
    return created
