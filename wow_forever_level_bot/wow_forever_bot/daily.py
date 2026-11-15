from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .commentary import CommentaryResult, CommentaryService, build_daily_payload
from .models import CharacterSnapshot, SnapshotProgress
from .news import NewsItem, WowheadNewsClient
from .store import Store
from .test_environment import (
    FIXTURE_ANCHOR,
    fixture_news,
    fixture_recent_commentary,
    prepare_fixture_store,
)

LOGGER = logging.getLogger("wow_forever_bot.daily")


@dataclass(frozen=True, slots=True)
class DailyBundle:
    progress: tuple[SnapshotProgress, ...]
    news: tuple[NewsItem, ...]
    payload: dict
    commentary: CommentaryResult
    generated_at: datetime
    synthetic: bool = False
    scenario: str | None = None
    news_error: str | None = None
    live_news: bool = False
    live_test: bool = False


async def build_live_daily_bundle(
    store: Store,
    guild_id: int,
    news_client: WowheadNewsClient,
    commentary_service: CommentaryService,
    *,
    as_of: datetime | None = None,
    news_lookback_hours: int = 24,
    max_news_items: int = 5,
) -> DailyBundle:
    generated_at = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    progress = await store.snapshot_progress(guild_id, generated_at)
    recent_commentary = await store.recent_commentary(guild_id, limit=5)
    news: list[NewsItem] = []
    news_error: str | None = None
    try:
        news = await news_client.fetch(
            since=generated_at - timedelta(hours=news_lookback_hours),
            until=generated_at,
            max_items=max_news_items,
        )
    except Exception as exc:  # The factual report must survive an RSS outage.
        news_error = str(exc)
        LOGGER.warning("Wowhead news unavailable: %s", exc)
    payload = build_daily_payload(
        progress,
        news,
        generated_at=generated_at,
        recent_commentary=recent_commentary,
    )
    commentary = await commentary_service.generate(payload)
    return DailyBundle(
        tuple(progress),
        tuple(news),
        payload,
        commentary,
        generated_at,
        news_error=news_error,
        live_news=True,
    )


async def build_live_test_daily_bundle(
    store: Store,
    guild_id: int,
    current_snapshots: list[CharacterSnapshot],
    news_client: WowheadNewsClient,
    commentary_service: CommentaryService,
    *,
    as_of: datetime | None = None,
    news_lookback_hours: int = 24,
    max_news_items: int = 5,
) -> DailyBundle:
    """Build a production-like report without writing snapshots, history or schedules."""

    generated_at = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    progress = await store.preview_progress_with_current(
        guild_id,
        current_snapshots,
        generated_at,
    )
    recent_commentary = await store.recent_commentary(guild_id, limit=5)
    news: list[NewsItem] = []
    news_error: str | None = None
    try:
        news = await news_client.fetch(
            since=generated_at - timedelta(hours=news_lookback_hours),
            until=generated_at,
            max_items=max_news_items,
        )
    except Exception as exc:  # The factual live test must survive an RSS outage.
        news_error = str(exc)
        LOGGER.warning("Wowhead news unavailable during live test: %s", exc)
    payload = build_daily_payload(
        progress,
        news,
        generated_at=generated_at,
        recent_commentary=recent_commentary,
    )
    commentary = await commentary_service.generate(payload)
    return DailyBundle(
        tuple(progress),
        tuple(news),
        payload,
        commentary,
        generated_at,
        news_error=news_error,
        live_news=True,
        live_test=True,
    )


async def build_fixture_daily_bundle(
    commentary_service: CommentaryService,
    *,
    scenario: str = "radio-day",
    root: str | Path = "/tmp/wow_forever_preview",
) -> DailyBundle:
    """Generate a preview from a unique, disposable DB and synthetic RSS items."""

    folder = Path(root) / f"{os.getpid()}-{uuid4().hex}"
    database = folder / "wow_forever-test.db"
    _, progress = await prepare_fixture_store(database, scenario=scenario, reset=True)
    news = fixture_news()
    payload = build_daily_payload(
        progress,
        news,
        generated_at=FIXTURE_ANCHOR,
        recent_commentary=fixture_recent_commentary(),
    )
    commentary = await commentary_service.generate(payload)
    return DailyBundle(
        tuple(progress),
        tuple(news),
        payload,
        commentary,
        FIXTURE_ANCHOR,
        synthetic=True,
        scenario=scenario,
    )


async def build_fixture_live_news_bundle(
    news_client: WowheadNewsClient,
    commentary_service: CommentaryService,
    *,
    scenario: str = "radio-day",
    root: str | Path = "/tmp/wow_forever_preview",
    as_of: datetime | None = None,
    news_lookback_hours: int = 24,
    max_news_items: int = 5,
) -> DailyBundle:
    """Combine isolated fixture history with the live Wowhead RSS feed.

    Character progress is built only from a unique test database under an
    approved test root. The production Store and scheduler are not accepted as
    inputs, so this path cannot read or mutate the live database or schedule.
    """

    generated_at = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    folder = Path(root) / f"{os.getpid()}-{uuid4().hex}"
    database = folder / "wow_forever-test.db"
    _, progress = await prepare_fixture_store(database, scenario=scenario, reset=True)

    news: list[NewsItem] = []
    news_error: str | None = None
    try:
        news = await news_client.fetch(
            since=generated_at - timedelta(hours=news_lookback_hours),
            until=generated_at,
            max_items=max_news_items,
        )
    except Exception as exc:  # The isolated report must survive an RSS outage.
        news_error = str(exc)
        LOGGER.warning("Wowhead news unavailable during isolated test: %s", exc)

    payload = build_daily_payload(
        progress,
        news,
        generated_at=generated_at,
        recent_commentary=fixture_recent_commentary(generated_at),
    )
    commentary = await commentary_service.generate(payload)
    return DailyBundle(
        tuple(progress),
        tuple(news),
        payload,
        commentary,
        generated_at,
        synthetic=True,
        scenario=scenario,
        news_error=news_error,
        live_news=True,
    )


def progress_summary_lines(progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress]) -> list[str]:
    lines: list[str] = []
    for row in progress:
        facts = [f"Level **{row.snapshot.level}**"]
        if row.levels_24h is not None:
            facts.append(f"24h **+{row.levels_24h}**")
        if row.levels_7d is not None:
            facts.append(f"7d **+{row.levels_7d}**")
        if row.rank is not None:
            movement = ""
            if row.rank_change:
                movement = f" ({'↑' if row.rank_change > 0 else '↓'}{abs(row.rank_change)})"
            facts.append(f"Rank **#{row.rank}**{movement}")
        if row.deaths_24h:
            facts.append(f"Deaths **+{row.deaths_24h}**")
        if row.honorable_kills_24h:
            facts.append(f"HKs **+{row.honorable_kills_24h}**")
        lines.append(f"**{row.snapshot.display_name}** — " + " · ".join(facts))
    return lines
