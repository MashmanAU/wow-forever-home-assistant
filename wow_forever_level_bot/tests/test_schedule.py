from datetime import datetime, timezone

import pytest

from wow_forever_bot.scheduling import (
    next_daily_run,
    parse_daily_time,
    sort_tracked_characters,
)
from wow_forever_bot.models import TrackedCharacter


def character(name: str, level: int | None) -> TrackedCharacter:
    first, surname = name.split()
    return TrackedCharacter(1, first, surname, "us", level, None)


def test_sort_highest_to_lowest_unknown_last_and_name_tiebreak() -> None:
    items = [
        character("Zulu Mage", 20),
        character("Alpha Druid", 20),
        character("Unknown Rogue", None),
        character("Top Warrior", 40),
    ]
    assert [item.display_name for item in sort_tracked_characters(items)] == [
        "Top Warrior",
        "Alpha Druid",
        "Zulu Mage",
        "Unknown Rogue",
    ]


def test_parse_time_rejects_non_24_hour_format() -> None:
    with pytest.raises(ValueError):
        parse_daily_time("8:30 pm")


def test_next_daily_run_uses_sydney_wall_clock() -> None:
    # 08:00 UTC is 19:00 AEDT on 8 November 2026.
    now = datetime(2026, 11, 8, 8, 0, tzinfo=timezone.utc)
    result = next_daily_run("20:30", "Australia/Sydney", now_utc=now)
    assert result == datetime(2026, 11, 8, 9, 30, tzinfo=timezone.utc)


def test_next_daily_run_rolls_to_tomorrow() -> None:
    now = datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc)  # 21:00 AEDT
    result = next_daily_run("20:30", "Australia/Sydney", now_utc=now)
    assert result == datetime(2026, 11, 9, 9, 30, tzinfo=timezone.utc)


def test_invalid_timezone_is_clear() -> None:
    with pytest.raises(ValueError, match="IANA"):
        next_daily_run("20:30", "Sydney")
