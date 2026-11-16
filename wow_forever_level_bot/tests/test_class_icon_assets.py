from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from wow_forever_bot import vendor_class_icons
from wow_forever_bot.vendor_class_icons import (
    CLASS_ICON_FILES,
    SOURCE_COMMIT,
    SOURCE_ROOT,
    validate_png,
)


def _png_header(width: int = 64, height: int = 64) -> bytes:
    output = BytesIO()
    Image.new("RGBA", (width, height), (40, 80, 120, 255)).save(output, format="PNG")
    return output.getvalue()


def test_icon_manifest_is_complete_pinned_and_classic_only() -> None:
    assert CLASS_ICON_FILES == (
        "druid.png",
        "hunter.png",
        "mage.png",
        "paladin.png",
        "priest.png",
        "rogue.png",
        "shaman.png",
        "warlock.png",
        "warrior.png",
    )
    assert len(SOURCE_COMMIT) == 40
    assert SOURCE_COMMIT in SOURCE_ROOT


def test_png_validator_accepts_only_expected_64px_assets() -> None:
    validate_png(_png_header())
    with pytest.raises(ValueError, match="not a valid PNG"):
        validate_png(b"not an image")
    with pytest.raises(ValueError, match="expected 64x64"):
        validate_png(_png_header(32, 32))


def test_vendor_step_writes_every_pinned_icon(tmp_path: Path, monkeypatch) -> None:
    png = _png_header()

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return png

    requested = []

    def fake_urlopen(request, timeout):
        requested.append((request.full_url, timeout))
        return _Response()

    monkeypatch.setattr(vendor_class_icons, "urlopen", fake_urlopen)
    vendor_class_icons.vendor_icons(tmp_path, timeout_seconds=12)
    assert tuple(path.name for path in sorted(tmp_path.glob("*.png"))) == tuple(sorted(CLASS_ICON_FILES))
    assert len(requested) == len(CLASS_ICON_FILES)
    assert all(SOURCE_COMMIT in url and timeout == 12 for url, timeout in requested)


def test_unlicense_and_source_notice_are_shipped() -> None:
    asset_dir = Path(__file__).resolve().parents[1] / "wow_forever_bot" / "assets" / "class_icons"
    notice = (asset_dir / "README.md").read_text()
    licence = (asset_dir / "UNLICENSE.txt").read_text()
    assert "orourkek/Wow-Icons" in notice
    assert SOURCE_COMMIT in notice
    assert "public domain" in licence