from pathlib import Path

import pytest

from workshop3d import brand_renderer


@pytest.mark.skipif(not brand_renderer._HAVE_PIL, reason="Pillow not installed")
def test_maker_and_patron_logos_stay_separate(tmp_path):
    from PIL import Image

    source = tmp_path / "source.png"
    maker = tmp_path / "maker.png"
    patron = tmp_path / "patron.png"
    Image.new("RGB", (300, 300), (50, 50, 60)).save(source)
    Image.new("RGBA", (30, 30), (255, 0, 0, 255)).save(maker)
    Image.new("RGBA", (30, 30), (0, 255, 0, 255)).save(patron)

    outputs = brand_renderer.render(
        source,
        tmp_path / "media",
        title="Czerwony Smok",
        brand="WorkShop3D",
        formats=["STL", "3MF"],
        logo_path=maker,
        patron_name="KF2.pl",
        patron_logo_path=patron,
    )
    cover = Path(next(path for path in outputs if path.endswith("cover.png")))
    with Image.open(cover) as image:
        # Maker at the top-left, patron independently at the top-right.
        assert image.getpixel((35, 35))[0] > 200
        assert image.getpixel((945, 35))[1] > 200
        assert image.size == (1200, 900)
