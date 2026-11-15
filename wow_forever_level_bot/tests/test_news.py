from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from wow_forever_bot.news import WowheadNewsClient, parse_wowhead_rss


UTC = timezone.utc
FIXTURE = Path(__file__).parent / "fixtures" / "wowhead_feed.xml"


def test_rss_parser_filters_by_time_topic_and_host() -> None:
    until = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)
    items = parse_wowhead_rss(
        FIXTURE.read_text(),
        since=until - timedelta(hours=24),
        until=until,
    )
    assert [item.title for item in items] == ["WoW Forever Hotfixes Improve Quest Credit"]
    assert items[0].url.startswith("https://www.wowhead.com/")


def test_rss_parser_rejects_invalid_xml() -> None:
    now = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="invalid RSS"):
        parse_wowhead_rss("<rss", since=now - timedelta(days=1), until=now)


def test_news_client_rejects_non_wowhead_url() -> None:
    with pytest.raises(ValueError, match="wowhead.com"):
        WowheadNewsClient("https://example.com/rss")
