from dataclasses import replace
from datetime import datetime, timezone

from wcwidth import wcswidth

from wow_forever_bot.config import Settings
from wow_forever_bot.models import (
    AchievementRecord,
    CharacterSnapshot,
    DeathCounters,
    ProfessionProgress,
    SnapshotProgress,
)
from wow_forever_bot.table_renderer import leaderboard_table, leaderboard_table_code_blocks


def _options(**changes):
    return replace(Settings("discord", "id", "secret"), **changes)


def _row(name: str = "Rbed Warr", *, rank: int = 1, movement: int | None = None) -> SnapshotProgress:
    first, surname = name.split(" ", 1)
    captured = datetime(2026, 11, 16, tzinfo=timezone.utc)
    return SnapshotProgress(
        snapshot=CharacterSnapshot(
            first,
            surname,
            "us",
            captured,
            43,
            character_class="Warrior",
            race="Night Elf",
            deaths=DeathCounters(lifetime=66),
            professions=(ProfessionProgress("bs", "Blacksmithing", "Classic", 152, 225),),
        ),
        levels_24h=movement,
        levels_7d=5,
        new_achievements_24h=(AchievementRecord(1, "Explore Burning Steppes", captured),),
        rank=rank,
    )


def test_core_columns_follow_the_agreed_order_and_zero_is_dash() -> None:
    table = leaderboard_table(
        [_row(), _row("Elrys Shadowbane", rank=2, movement=3)],
        options=_options(show_7d_changes=True, show_rank=False),
    )
    header = table.splitlines()[0]
    assert header.index("Character") < header.index("Level") < header.index("24h")
    assert header.index("24h") < header.index("7d") < header.index("Deaths")
    assert "43   -  +5     66" in table
    assert "43  +3  +5     66" in table
    assert "+0" not in table
    assert "/60" not in table


def test_unicode_widths_and_long_optional_details_stay_mobile_conscious() -> None:
    rows = [
        _row("Zuturi 龍", rank=1, movement=1),
        _row("Verylongcharacter Name", rank=2, movement=None),
    ]
    table = leaderboard_table(
        rows,
        options=_options(
            show_rank=True,
            show_race=True,
            show_class=True,
            show_level_progress=True,
            show_professions=True,
            show_notable_activity=True,
        ),
    )
    lines = table.splitlines()
    assert "Details" in lines[0]
    assert all(wcswidth(line) <= 58 for line in lines)
    assert "Warrior" in table
    assert "Night" in table and "Elf" in table
    assert "BS 152" in table
    assert "Explore" in table


def test_large_rosters_are_split_into_safe_repeated_header_code_blocks() -> None:
    rows = [_row(f"Player{i} Name", rank=i, movement=i % 3) for i in range(1, 121)]
    blocks = leaderboard_table_code_blocks(rows, options=_options(), limit=900)
    assert len(blocks) > 1
    assert all(block.startswith("```text\nCharacter") for block in blocks)
    assert all(block.endswith("\n```") and len(block) <= 900 for block in blocks)
    assert sum(block.count("Player") for block in blocks) == 120
