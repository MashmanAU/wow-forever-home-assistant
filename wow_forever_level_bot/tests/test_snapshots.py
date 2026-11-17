import asyncio
from datetime import datetime, timedelta, timezone

from wow_forever_bot.blizzard import (
    character_slug,
    parse_achievements,
    parse_death_counters,
    parse_professions,
)
from wow_forever_bot.models import (
    AchievementRecord,
    CharacterProfile,
    CharacterSnapshot,
    DeathCounters,
    ProfessionProgress,
)
from wow_forever_bot.store import Store

UTC = timezone.utc


def snapshot(
    name: str,
    surname: str,
    captured_at: datetime,
    level: int,
    experience: int,
    deaths: int,
    achievement_ids: tuple[int, ...] = (),
    profession_skill: int = 0,
) -> CharacterSnapshot:
    return CharacterSnapshot(
        first_name=name,
        surname=surname,
        region="us",
        captured_at=captured_at,
        level=level,
        experience=experience,
        average_item_level=float(level),
        equipped_item_level=float(level - 1),
        honorable_kills=level,
        deaths=DeathCounters(
            lifetime=deaths,
            falling=max(0, deaths - 5),
            drowning=1,
            fire_lava=0,
            pvp=max(0, deaths - 3),
            dungeon_raid=1,
        ),
        achievements=tuple(
            AchievementRecord(item, f"Achievement {item}", captured_at)
            for item in achievement_ids
        ),
        professions=(
            ProfessionProgress("profession:164:tier:2477", "Blacksmithing", "Classic", profession_skill, 150),
        ),
    )


def test_character_slug_uses_one_realmless_path_segment() -> None:
    assert character_slug("Storm", "Hound") == "storm-hound"
    assert character_slug("  Mash ", " Man ") == "mash-man"


def test_death_parser_selects_general_death_statistics_not_context_total() -> None:
    payload = {
        "categories": [
            {
                "name": "Player vs. Player Statistics",
                "statistics": [
                    {"id": 1, "name": "Total deaths from other players", "quantity": 27}
                ],
            },
            {
                "name": "Death Statistics",
                "statistics": [{"id": 60, "name": "Total deaths", "quantity": 7}],
                "sub_categories": [
                    {
                        "name": "Environmental Deaths",
                        "statistics": [
                            {"id": 61, "name": "Deaths from drowning", "quantity": 1}
                        ],
                    }
                ],
            },
            {
                "name": "Deaths by location",
                "statistics": [{"id": 70, "name": "Total deaths", "quantity": 40}],
                "sub_categories": [
                    {
                        "statistics": [
                            {"name": "Total raid and dungeon deaths", "quantity": 1},
                            {"name": "Deaths from falling", "quantity": 2},
                        ]
                    }
                ],
            },
        ]
    }
    deaths = parse_death_counters(payload)
    assert deaths.lifetime == 7
    assert deaths.pvp == 27
    assert deaths.drowning == 1
    assert deaths.falling == 2
    assert deaths.dungeon_raid == 1


def test_death_parser_refuses_ambiguous_unlabelled_totals() -> None:
    payload = {
        "categories": [
            {"statistics": [{"name": "Total deaths", "quantity": 7}]},
            {"statistics": [{"name": "Total deaths", "quantity": 40}]},
        ]
    }
    assert parse_death_counters(payload).lifetime is None


def test_achievement_and_profession_parsers_use_ids_not_positions() -> None:
    achievements = parse_achievements(
        {
            "achievements": [
                {
                    "achievement": {"id": 456, "name": "Second"},
                    "completed_timestamp": 1_794_547_980_000,
                },
                {"id": 123, "name": "First", "completed_timestamp": 1_794_545_940_000},
            ]
        }
    )
    assert [item.achievement_id for item in achievements] == [123, 456]
    assert achievements[0].completed_at is not None

    professions = parse_professions(
        {
            "primaries": [
                {
                    "profession": {"id": 164, "name": "Blacksmithing"},
                    "tiers": [
                        {
                            "tier": {"id": 2477, "name": "Classic"},
                            "skill_points": 111,
                            "max_skill_points": 150,
                        }
                    ],
                }
            ]
        }
    )
    assert professions[0].key == "profession:164:tier:2477"
    assert professions[0].skill_points == 111


def test_snapshot_round_trip_and_progress_derivation(tmp_path) -> None:
    async def scenario() -> None:
        store = Store(str(tmp_path / "bot.db"))
        await store.initialize()
        mash = CharacterProfile("Mash", "Man", "us", 21)
        storm = CharacterProfile("Storm", "Hound", "us", 22)
        assert await store.add_character(10, mash, 99)
        assert await store.add_character(10, storm, 99)

        current_at = datetime(2026, 11, 14, 9, 5, tzinfo=UTC)
        day = current_at - timedelta(hours=24, minutes=5)
        week = current_at - timedelta(days=7, minutes=5)

        # Mash moves from second to first and gains a level, a death, an
        # achievement and three profession points.
        await store.save_snapshot(10, snapshot("Mash", "Man", week, 18, 100, 5, (1,), 100))
        await store.save_snapshot(10, snapshot("Storm", "Hound", week, 19, 100, 9, (2,), 80))
        await store.save_snapshot(10, snapshot("Mash", "Man", day, 20, 500, 7, (1,), 108))
        await store.save_snapshot(10, snapshot("Storm", "Hound", day, 21, 400, 10, (2,), 80))
        await store.save_snapshot(10, snapshot("Mash", "Man", current_at, 22, 200, 8, (1, 3), 111))
        await store.save_snapshot(10, snapshot("Storm", "Hound", current_at, 21, 900, 10, (2,), 80))

        rows = await store.list_snapshots(10, "Mash", "Man", "us")
        assert len(rows) == 3
        assert rows[-1].deaths.lifetime == 8
        assert [item.achievement_id for item in rows[-1].achievements] == [1, 3]

        progress = await store.snapshot_progress(10, current_at)
        assert [item.snapshot.display_name for item in progress] == ["Mash Man", "Storm Hound"]
        mash_progress = progress[0]
        assert mash_progress.rank == 1
        assert mash_progress.rank_change == 1
        assert mash_progress.levels_24h == 2
        assert mash_progress.levels_7d == 4
        assert mash_progress.deaths_24h == 1
        assert [item.achievement_id for item in mash_progress.new_achievements_24h] == [3]
        assert mash_progress.profession_skill_gains_24h == (("Blacksmithing — Classic", 3),)
        assert mash_progress.days_since_last_level == 0.0

        # Character removal also removes its historical snapshots.
        assert await store.remove_character(10, "Mash", "Man", "us")
        assert await store.list_snapshots(10, "Mash", "Man", "us") == []

    asyncio.run(scenario())


def test_24h_baseline_uses_nearest_daily_snapshot_despite_scheduler_jitter(tmp_path) -> None:
    async def scenario() -> None:
        store = Store(str(tmp_path / "jitter.db"))
        await store.initialize()
        profile = CharacterProfile("Elrys", "Shadowbane", "us", 40)
        assert await store.add_character(10, profile, 99)

        current_at = datetime(2026, 11, 16, 5, 30, tzinfo=UTC)
        two_days_ago = current_at - timedelta(hours=47, minutes=55)
        yesterday = current_at - timedelta(hours=23, minutes=55)
        await store.save_snapshot(
            10, snapshot("Elrys", "Shadowbane", two_days_ago, 38, 0, 0)
        )
        await store.save_snapshot(
            10, snapshot("Elrys", "Shadowbane", yesterday, 39, 0, 0)
        )
        await store.save_snapshot(
            10, snapshot("Elrys", "Shadowbane", current_at, 40, 0, 0)
        )

        progress = await store.snapshot_progress(10, current_at)
        assert len(progress) == 1
        assert progress[0].baseline_24h_at == yesterday
        assert progress[0].levels_24h == 1

    asyncio.run(scenario())


def test_24h_delta_is_unknown_without_a_near_daily_baseline(tmp_path) -> None:
    async def scenario() -> None:
        store = Store(str(tmp_path / "stale.db"))
        await store.initialize()
        profile = CharacterProfile("Elrys", "Shadowbane", "us", 40)
        assert await store.add_character(10, profile, 99)

        current_at = datetime(2026, 11, 16, 5, 30, tzinfo=UTC)
        stale = current_at - timedelta(hours=40)
        await store.save_snapshot(10, snapshot("Elrys", "Shadowbane", stale, 38, 0, 0))
        await store.save_snapshot(10, snapshot("Elrys", "Shadowbane", current_at, 40, 0, 0))

        progress = await store.snapshot_progress(10, current_at)
        assert progress[0].baseline_24h_at is None
        assert progress[0].levels_24h is None

    asyncio.run(scenario())
