from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO

from PIL import Image

from wow_forever_bot.config import Settings
from wow_forever_bot.image_renderer import render_leaderboard_png
from wow_forever_bot.models import (
    CharacterSnapshot,
    DeathCounters,
    ProfessionProgress,
    SnapshotProgress,
)


def _options(**changes):
    base = Settings("discord", "id", "secret")
    return replace(base, **changes)


def _rows() -> tuple[SnapshotProgress, ...]:
    captured = datetime(2026, 11, 16, tzinfo=timezone.utc)
    rows = []
    for rank, (first, surname, character_class, level) in enumerate(
        (
            ("Rbed", "Warr", "Warrior", 43),
            ("Lutherr", "Dawnguard", "Paladin", 39),
            ("Dead", "Fall", "Warrior", 39),
        ),
        start=1,
    ):
        snapshot = CharacterSnapshot(
            first,
            surname,
            "us",
            captured,
            level,
            character_class=character_class,
            race="Dwarf" if rank > 1 else "Night Elf",
            deaths=DeathCounters(lifetime=rank * 10),
            professions=(
                ProfessionProgress("first-aid", "First Aid", "Classic", 100 + rank, 225),
            ),
        )
        rows.append(SnapshotProgress(snapshot=snapshot, rank=rank))
    return tuple(rows)


def test_image_renderer_is_deterministic_and_valid_png() -> None:
    generated_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
    first = render_leaderboard_png(_rows(), options=_options(), generated_at=generated_at)
    second = render_leaderboard_png(_rows(), options=_options(), generated_at=generated_at)
    assert first == second
    assert first.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(BytesIO(first))
    assert image.mode == "RGB"
    assert image.width == 1600
    assert image.height > 400


def test_one_column_and_theme_controls_change_output() -> None:
    generated_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
    two_column = render_leaderboard_png(_rows(), options=_options(), generated_at=generated_at)
    one_column = render_leaderboard_png(
        _rows(),
        options=_options(image_columns="one", image_theme="parchment"),
        generated_at=generated_at,
    )
    image = Image.open(BytesIO(one_column))
    assert image.width == 1000
    assert one_column != two_column
