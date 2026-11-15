import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

from wow_forever_bot.models import CharacterProfile, DailySchedule
from wow_forever_bot.store import Store


def test_store_character_and_schedule_round_trip(tmp_path) -> None:
    async def scenario() -> None:
        store = Store(str(tmp_path / "bot.db"))
        await store.initialize()
        profile = CharacterProfile("Judgement", "Judy", "eu", 27)
        assert await store.add_character(10, profile, 99) is True
        assert await store.add_character(10, profile, 99) is False
        rows = await store.list_characters(10)
        assert len(rows) == 1
        assert rows[0].level == 27

        next_run = datetime(2026, 11, 8, 9, 30, tzinfo=timezone.utc)
        await store.set_schedule(DailySchedule(10, 20, "20:30", "Australia/Sydney", next_run))
        assert len(await store.due_schedules(next_run)) == 1
        assert await store.disable_schedule(10) is True

    asyncio.run(scenario())


def test_migrates_legacy_interval_schedule(tmp_path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE schedules (guild_id INTEGER PRIMARY KEY, channel_id INTEGER NOT NULL, interval_hours INTEGER NOT NULL, next_run_at TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO schedules VALUES (1, 2, 24, '2026-11-08T09:30:00+00:00')"
        )
    async def scenario() -> None:
        store = Store(str(path), "Australia/Sydney")
        await store.initialize()
        schedules = await store.all_schedules()
        assert len(schedules) == 1
        assert schedules[0].time_of_day == "20:30"
        assert schedules[0].timezone == "Australia/Sydney"

    asyncio.run(scenario())


def test_commentary_history_round_trip_and_retention(tmp_path) -> None:
    async def scenario() -> None:
        store = Store(str(tmp_path / "history.db"))
        await store.initialize()
        for day in range(35):
            await store.save_commentary(
                10,
                generated_at=datetime(2026, 10, 1, 9, tzinfo=timezone.utc)
                + timedelta(days=day),
                text=f"Bulletin {day}",
                source="openai",
                story_angle="gear-and-craft" if day % 2 else "pvp-desk",
            )
        recent = await store.recent_commentary(10, limit=5)
        assert [item.text for item in recent] == [
            "Bulletin 34",
            "Bulletin 33",
            "Bulletin 32",
            "Bulletin 31",
            "Bulletin 30",
        ]
        with sqlite3.connect(tmp_path / "history.db") as db:
            assert db.execute(
                "SELECT COUNT(*) FROM commentary_history WHERE guild_id=10"
            ).fetchone()[0] == 30
            assert db.execute("PRAGMA user_version").fetchone()[0] == 150

    asyncio.run(scenario())
