from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFont

from wow_forever_bot.config import Settings
from wow_forever_bot.rendering import _font, _font_path
from wow_forever_bot.minimal_image_renderer import render_minimal_leaderboard_png
from wow_forever_bot.models import CharacterSnapshot, DeathCounters, SnapshotProgress


def _options(**changes):
    return replace(Settings("discord", "id", "secret"), **changes)


def _rows() -> tuple[SnapshotProgress, ...]:
    captured = datetime(2026, 11, 16, tzinfo=timezone.utc)
    values = (
        ("Rbed", "Warr", "Warrior", 43, 1),
        ("Elrys", "Shadowbane", "Hunter", 40, 3),
        ("Lutherr", "Dawnguard", "Paladin", 40, None),
    )
    return tuple(
        SnapshotProgress(
            snapshot=CharacterSnapshot(
                first,
                surname,
                "us",
                captured,
                level,
                character_class=character_class,
                race="Night Elf",
                deaths=DeathCounters(lifetime=rank * 10),
            ),
            levels_24h=movement,
            rank=rank,
        )
        for rank, (first, surname, character_class, level, movement) in enumerate(values, 1)
    )


def test_minimal_image_is_narrow_deterministic_and_large_type() -> None:
    generated_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
    first = render_minimal_leaderboard_png(_rows(), options=_options(), generated_at=generated_at)
    second = render_minimal_leaderboard_png(_rows(), options=_options(), generated_at=generated_at)
    assert first == second
    assert first.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(BytesIO(first))
    assert image.mode == "RGB"
    assert image.size == (540, 170)


def test_secondary_fields_expand_rows_only_when_enabled() -> None:
    generated_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
    minimal = render_minimal_leaderboard_png(_rows(), options=_options(), generated_at=generated_at)
    expanded = render_minimal_leaderboard_png(
        _rows(),
        options=_options(show_race=True, show_class=True, show_7d_changes=True),
        generated_at=generated_at,
    )
    assert Image.open(BytesIO(minimal)).height == 170
    assert Image.open(BytesIO(expanded)).height == 224
    assert expanded != minimal


def test_full_roster_uses_compact_reference_like_dimensions() -> None:
    generated_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
    rows = _rows() * 6
    image = Image.open(
        BytesIO(
            render_minimal_leaderboard_png(
                rows,
                options=_options(),
                generated_at=generated_at,
            )
        )
    )
    assert image.size == (540, 980)
    assert 54 <= image.height / len(rows) <= 55


def test_requested_typography_uses_a_scalable_bold_font() -> None:
    font = _font(27, bold=True, condensed=True)
    assert isinstance(font, ImageFont.FreeTypeFont)
    assert font.size == 27


def test_alpine_dejavu_directory_is_searched(monkeypatch) -> None:
    expected = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"

    def fake_exists(path: Path) -> bool:
        return str(path) == expected

    monkeypatch.setattr(Path, "exists", fake_exists)
    assert _font_path("DejaVuSans-Bold.ttf") == expected
