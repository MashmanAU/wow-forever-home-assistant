import asyncio
import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from wow_forever_bot.commentary import CommentaryService
from wow_forever_bot.daily import (
    build_fixture_live_news_bundle,
    build_live_daily_bundle,
    build_live_test_daily_bundle,
)
from wow_forever_bot.models import DailySchedule
from wow_forever_bot.news import NewsItem
from wow_forever_bot.test_environment import (
    FIXTURE_ANCHOR,
    FIXTURE_GUILD_ID,
    prepare_fixture_store,
)


class FailingNewsClient:
    async def fetch(self, **kwargs):
        raise RuntimeError("synthetic RSS outage")


class RecordingNewsClient:
    def __init__(self) -> None:
        self.request = None

    async def fetch(self, **kwargs):
        self.request = kwargs
        return [
            NewsItem(
                "Live Wowhead test headline",
                "https://www.wowhead.com/news/live-test-100003",
                kwargs["until"] - timedelta(hours=1),
                "Not sent to OpenAI.",
            )
        ]


def test_rss_failure_still_builds_factual_daily_bundle(tmp_path: Path) -> None:
    async def scenario() -> None:
        store, _ = await prepare_fixture_store(tmp_path / "outage.db")
        await store.save_commentary(
            FIXTURE_GUILD_ID,
            generated_at=FIXTURE_ANCHOR - timedelta(days=1),
            text="Previous posted bulletin.",
            source="openai",
            story_angle="level-race",
        )
        commentary = CommentaryService("")
        try:
            bundle = await build_live_daily_bundle(
                store,
                FIXTURE_GUILD_ID,
                FailingNewsClient(),
                commentary,
                as_of=FIXTURE_ANCHOR,
            )
        finally:
            await commentary.close()
        assert bundle.progress
        assert bundle.news == ()
        assert bundle.news_error == "synthetic RSS outage"
        assert bundle.commentary.source == "deterministic-fallback"
        assert bundle.payload["commentary_direction"]["recent_commentary"][0][
            "text_for_anti_repetition_only"
        ] == "Previous posted bulletin."

    asyncio.run(scenario())


def test_fixture_live_news_bundle_isolated_from_live_store_and_schedule(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        news = RecordingNewsClient()
        commentary = CommentaryService("")
        try:
            bundle = await build_fixture_live_news_bundle(
                news,
                commentary,
                scenario="comeback",
                root=tmp_path,
                as_of=FIXTURE_ANCHOR + timedelta(days=30),
                news_lookback_hours=36,
            )
        finally:
            await commentary.close()

        assert bundle.synthetic is True
        assert bundle.live_news is True
        assert bundle.scenario == "comeback"
        assert bundle.progress
        assert bundle.news[0].title == "Live Wowhead test headline"
        assert bundle.news_error is None
        assert bundle.commentary.source == "deterministic-fallback"
        assert news.request["until"] == FIXTURE_ANCHOR + timedelta(days=30)
        assert news.request["since"] == FIXTURE_ANCHOR + timedelta(days=30, hours=-36)
        assert list(tmp_path.rglob("wow_forever-test.db"))

    asyncio.run(scenario())


def test_fixture_live_news_outage_does_not_fall_back_to_synthetic_news(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        commentary = CommentaryService("")
        try:
            bundle = await build_fixture_live_news_bundle(
                FailingNewsClient(),
                commentary,
                root=tmp_path,
                as_of=FIXTURE_ANCHOR,
            )
        finally:
            await commentary.close()

        assert bundle.synthetic is True
        assert bundle.live_news is True
        assert bundle.news == ()
        assert bundle.news_error == "synthetic RSS outage"
        assert bundle.progress

    asyncio.run(scenario())


def test_live_test_bundle_uses_ephemeral_current_snapshots_without_writes(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        database = tmp_path / "live-test.db"
        store, _ = await prepare_fixture_store(database)
        next_run = FIXTURE_ANCHOR + timedelta(days=1)
        await store.set_schedule(
            DailySchedule(
                FIXTURE_GUILD_ID,
                987654,
                "09:00",
                "Australia/Sydney",
                next_run,
            )
        )
        await store.save_commentary(
            FIXTURE_GUILD_ID,
            generated_at=FIXTURE_ANCHOR - timedelta(days=1),
            text="Stored production bulletin.",
            source="openai",
            story_angle="level-race",
        )
        history = await store.list_snapshots(FIXTURE_GUILD_ID)
        latest_by_character = {}
        for snapshot in history:
            key = (snapshot.first_name.casefold(), snapshot.surname.casefold(), snapshot.region)
            latest_by_character[key] = snapshot
        live_time = FIXTURE_ANCHOR + timedelta(hours=6)
        current = [
            replace(snapshot, captured_at=live_time, level=snapshot.level + 1)
            for snapshot in latest_by_character.values()
        ]

        def persisted_state():
            with sqlite3.connect(database) as db:
                return {
                    "snapshots": db.execute(
                        "SELECT COUNT(*) FROM character_snapshots"
                    ).fetchone()[0],
                    "commentary": db.execute(
                        "SELECT guild_id, generated_at, text, source, story_angle "
                        "FROM commentary_history ORDER BY id"
                    ).fetchall(),
                    "schedule": db.execute(
                        "SELECT guild_id, channel_id, time_of_day, timezone, next_run_utc "
                        "FROM schedules ORDER BY guild_id"
                    ).fetchall(),
                    "characters": db.execute(
                        "SELECT guild_id, first_name, surname, region, level, last_checked_at "
                        "FROM characters ORDER BY first_name, surname"
                    ).fetchall(),
                }

        before = persisted_state()
        commentary = CommentaryService("")
        try:
            bundle = await build_live_test_daily_bundle(
                store,
                FIXTURE_GUILD_ID,
                current,
                RecordingNewsClient(),
                commentary,
                as_of=live_time,
            )
        finally:
            await commentary.close()
        after = persisted_state()

        assert after == before
        assert bundle.live_test is True
        assert bundle.synthetic is False
        assert bundle.live_news is True
        assert len(bundle.progress) == len(current)
        assert all(row.snapshot.captured_at == live_time for row in bundle.progress)
        assert bundle.payload["commentary_direction"]["recent_commentary"][0][
            "text_for_anti_repetition_only"
        ] == "Stored production bulletin."

    asyncio.run(scenario())
