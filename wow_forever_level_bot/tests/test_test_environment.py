import asyncio
from pathlib import Path

import pytest

from wow_forever_bot.daily import build_fixture_daily_bundle
from wow_forever_bot.commentary import CommentaryService
from wow_forever_bot.test_environment import (
    FIXTURE_ANCHOR,
    SCENARIOS,
    prepare_fixture_store,
    validate_test_database_path,
)


def test_live_database_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="live database"):
        validate_test_database_path("/data/wow_forever.db")


def test_unapproved_test_database_root_is_rejected() -> None:
    with pytest.raises(ValueError, match="/tmp or /data/wow_forever-test"):
        validate_test_database_path("/share/looks-like-a-test.db")


def test_fixture_histories_are_deterministic_and_schedule_free(tmp_path: Path) -> None:
    async def scenario() -> None:
        store_a, progress_a = await prepare_fixture_store(tmp_path / "a.db")
        store_b, progress_b = await prepare_fixture_store(tmp_path / "b.db")
        comparable_a = [
            (row.snapshot.display_name, row.snapshot.level, row.levels_24h, row.levels_7d, row.deaths_24h)
            for row in progress_a
        ]
        comparable_b = [
            (row.snapshot.display_name, row.snapshot.level, row.levels_24h, row.levels_7d, row.deaths_24h)
            for row in progress_b
        ]
        assert comparable_a == comparable_b
        assert await store_a.all_schedules() == []
        assert await store_b.all_schedules() == []
        assert max(row.snapshot.captured_at for row in progress_a) == FIXTURE_ANCHOR

    asyncio.run(scenario())


def test_every_preview_scenario_builds_without_live_credentials(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = CommentaryService("")
        try:
            for name in SCENARIOS:
                bundle = await build_fixture_daily_bundle(
                    service,
                    scenario=name,
                    root=tmp_path,
                )
                assert bundle.synthetic is True
                assert bundle.scenario == name
                assert bundle.progress
                assert bundle.news
                assert bundle.payload["story_candidates"]
                assert bundle.commentary.story_angle
                assert len(bundle.commentary.text.split()) <= 75
        finally:
            await service.close()

    asyncio.run(scenario())
