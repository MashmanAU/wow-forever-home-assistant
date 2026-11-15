from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import (
    AchievementRecord,
    CharacterProfile,
    CharacterSnapshot,
    CommentaryHistoryEntry,
    DeathCounters,
    ProfessionProgress,
    SnapshotProgress,
)
from .news import NewsItem
from .store import Store

FIXTURE_GUILD_ID = 1_400_001
FIXTURE_ANCHOR = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)
SCENARIOS = (
    "radio-day",
    "quiet-day",
    "comeback",
    "crafting-day",
    "pvp-night",
)
LIVE_DATABASE = Path("/data/wow_forever.db")


def validate_test_database_path(path: str | Path) -> Path:
    target = Path(path).expanduser().resolve()
    if target == LIVE_DATABASE.resolve():
        raise ValueError("Refusing to use the live database as a test database")
    permitted = (Path("/tmp").resolve(), Path("/data/wow_forever-test").resolve())
    if not any(target == root or root in target.parents for root in permitted):
        raise ValueError("Test databases must be under /tmp or /data/wow_forever-test")
    return target


def fixture_news() -> list[NewsItem]:
    return [
        NewsItem(
            "Darkmoon Faire Opens Tomorrow on WoW Forever Realms",
            "https://www.wowhead.com/news/darkmoon-faire-forever-100001",
            FIXTURE_ANCHOR - timedelta(hours=3),
            "A deterministic synthetic headline used only for preview testing.",
        ),
        NewsItem(
            "WoW Forever Hotfixes Improve Quest Credit",
            "https://www.wowhead.com/news/forever-hotfixes-100002",
            FIXTURE_ANCHOR - timedelta(hours=10),
            "A deterministic synthetic headline used only for preview testing.",
        ),
    ]


def fixture_recent_commentary(
    anchor: datetime = FIXTURE_ANCHOR,
) -> list[CommentaryHistoryEntry]:
    """Fixed style memory for previews; it is never sourced from the live database."""

    return [
        CommentaryHistoryEntry(
            anchor - timedelta(days=1),
            "Good morning, guildmates! Mash Man levelled while Dead Fall died. Keep leveling and stay epic!",
            "synthetic-history",
            "level-race",
        ),
        CommentaryHistoryEntry(
            anchor - timedelta(days=2),
            "Looks like the spirit healer saw traffic again. Time to make today legendary!",
            "synthetic-history",
            "survival-report",
        ),
        CommentaryHistoryEntry(
            anchor - timedelta(days=3),
            "Azeroth news is live, champions. The latest headline leads today's adventure.",
            "synthetic-history",
            "news-flash",
        ),
    ]


def _snapshot(
    first_name: str,
    surname: str,
    captured_at: datetime,
    *,
    level: int,
    experience: int,
    deaths: int,
    falling: int,
    honorable_kills: int,
    item_level: float,
    achievements: tuple[tuple[int, str], ...] = (),
    profession_skill: int = 0,
) -> CharacterSnapshot:
    return CharacterSnapshot(
        first_name=first_name,
        surname=surname,
        region="us",
        captured_at=captured_at,
        level=level,
        experience=experience,
        average_item_level=item_level,
        equipped_item_level=item_level - 0.5,
        character_class="Synthetic class",
        race="Synthetic race",
        faction="Synthetic faction",
        ruleset="Forever",
        honorable_kills=honorable_kills,
        deaths=DeathCounters(
            lifetime=deaths,
            falling=falling,
            drowning=0,
            fire_lava=0,
            pvp=max(0, deaths - falling - 2),
            dungeon_raid=1,
        ),
        achievements=tuple(
            AchievementRecord(achievement_id, name, captured_at)
            for achievement_id, name in achievements
        ),
        professions=(
            ProfessionProgress(
                "profession:164:tier:2477",
                "Blacksmithing",
                "Classic",
                profession_skill,
                150,
            ),
        ),
    )


def _history(scenario: str) -> dict[tuple[str, str], list[CharacterSnapshot]]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    week = FIXTURE_ANCHOR - timedelta(days=7, minutes=5)
    day = FIXTURE_ANCHOR - timedelta(hours=24, minutes=5)
    now = FIXTURE_ANCHOR

    quiet = scenario in {"quiet-day", "crafting-day", "pvp-night"}
    comeback = scenario == "comeback"
    crafting = scenario == "crafting-day"
    pvp_night = scenario == "pvp-night"
    mash_day_level = 35 if comeback else 34
    mash_now_level = mash_day_level if quiet else mash_day_level + 2
    storm_day_level = 36 if comeback else 35
    storm_now_level = storm_day_level
    egg_day_level = 33
    egg_now_level = egg_day_level if quiet else egg_day_level + 1

    return {
        ("Mash", "Man"): [
            _snapshot("Mash", "Man", week, level=31, experience=200, deaths=7, falling=1, honorable_kills=5, item_level=32.0, achievements=((1, "First Steps"),), profession_skill=104),
            _snapshot("Mash", "Man", day, level=mash_day_level, experience=500, deaths=8, falling=1, honorable_kills=7, item_level=35.0, achievements=((1, "First Steps"),), profession_skill=110),
            _snapshot(
                "Mash",
                "Man",
                now,
                level=mash_now_level,
                experience=900 if pvp_night else (500 if quiet else 250),
                deaths=8 if quiet else 9,
                falling=1 if quiet else 2,
                honorable_kills=15 if pvp_night else (7 if quiet else 10),
                item_level=37.5 if crafting or not quiet else 35.0,
                achievements=(
                    ((1, "First Steps"), (3, "Hammer Time"))
                    if crafting
                    else (((1, "First Steps"),) if quiet else ((1, "First Steps"), (2, "Going Up")))
                ),
                profession_skill=118 if crafting else (110 if quiet else 114),
            ),
        ],
        ("Storm", "Hound"): [
            _snapshot("Storm", "Hound", week, level=33, experience=100, deaths=4, falling=0, honorable_kills=15, item_level=34.0, profession_skill=80),
            _snapshot("Storm", "Hound", day, level=storm_day_level, experience=700, deaths=5, falling=0, honorable_kills=17, item_level=36.0, profession_skill=82),
            _snapshot(
                "Storm",
                "Hound",
                now,
                level=storm_now_level,
                experience=930 if pvp_night or not quiet else 700,
                deaths=5,
                falling=0,
                honorable_kills=25 if pvp_night else (17 if quiet else 18),
                item_level=36.0,
                profession_skill=82,
            ),
        ],
        ("Man", "Egg"): [
            _snapshot("Man", "Egg", week, level=29, experience=300, deaths=11, falling=3, honorable_kills=2, item_level=30.0, profession_skill=50),
            _snapshot("Man", "Egg", day, level=egg_day_level, experience=400, deaths=12, falling=3, honorable_kills=2, item_level=33.0, profession_skill=55),
            _snapshot(
                "Man",
                "Egg",
                now,
                level=egg_now_level,
                experience=400 if quiet else 100,
                deaths=12,
                falling=3,
                honorable_kills=2,
                item_level=34.0 if crafting or not quiet else 33.0,
                profession_skill=61 if crafting or not quiet else 55,
            ),
        ],
        ("Dead", "Fall"): [
            _snapshot("Dead", "Fall", week, level=34, experience=100, deaths=20, falling=9, honorable_kills=0, item_level=34.0, profession_skill=30),
            _snapshot("Dead", "Fall", day, level=37, experience=500, deaths=22, falling=10, honorable_kills=0, item_level=37.0, profession_skill=30),
            _snapshot("Dead", "Fall", now, level=37, experience=500 if quiet else 650, deaths=22 if quiet else 23, falling=10 if quiet else 11, honorable_kills=0, item_level=37.0, profession_skill=30),
        ],
    }


async def prepare_fixture_store(
    database_path: str | Path,
    *,
    scenario: str = "radio-day",
    reset: bool = True,
) -> tuple[Store, list[SnapshotProgress]]:
    """Create a deterministic, disposable store that cannot target the live DB."""

    target = validate_test_database_path(database_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if reset:
        for candidate in (target, Path(str(target) + "-wal"), Path(str(target) + "-shm")):
            candidate.unlink(missing_ok=True)

    store = Store(str(target))
    await store.initialize()
    histories = _history(scenario)
    for (first_name, surname), snapshots in histories.items():
        await store.add_character(
            FIXTURE_GUILD_ID,
            CharacterProfile(first_name, surname, "us", snapshots[-1].level),
            added_by=0,
        )
        for snapshot in snapshots:
            await store.save_snapshot(FIXTURE_GUILD_ID, snapshot)
    progress = await store.snapshot_progress(FIXTURE_GUILD_ID, FIXTURE_ANCHOR)
    return store, progress
