from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree

import aiohttp

DEFAULT_WOWHEAD_FEED = "https://www.wowhead.com/news/rss/all"
DEFAULT_KEYWORDS = (
    "wow forever",
    "world of warcraft forever",
    "forever realms",
    "forever realm",
    "forever hardcore",
)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class NewsItem:
    title: str
    url: str
    published_at: datetime
    summary: str = ""

    def to_payload(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at.astimezone(timezone.utc).isoformat(),
            "summary": self.summary,
        }


def _clean(value: str | None, limit: int) -> str:
    text = html.unescape(_TAG_RE.sub(" ", value or ""))
    text = _SPACE_RE.sub(" ", text).strip()
    return text[:limit]


def _published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_wowhead_rss(
    xml_text: str,
    *,
    since: datetime,
    until: datetime,
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
    max_items: int = 5,
) -> list[NewsItem]:
    """Parse and tightly filter a Wowhead RSS document.

    Only headline/summary text is consumed. Article bodies are never fetched.
    The caller supplies both time boundaries to make test results deterministic.
    """

    since_utc = since.astimezone(timezone.utc)
    until_utc = until.astimezone(timezone.utc)
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("Wowhead returned invalid RSS XML") from exc

    lowered_keywords = tuple(item.casefold().strip() for item in keywords if item.strip())
    output: list[NewsItem] = []
    for node in root.findall(".//item"):
        title = _clean(node.findtext("title"), 240)
        summary = _clean(node.findtext("description"), 480)
        link = (node.findtext("link") or "").strip()
        published = _published(node.findtext("pubDate"))
        if not title or not link or published is None:
            continue
        parsed_link = urlparse(link)
        if parsed_link.scheme != "https" or parsed_link.hostname not in {
            "wowhead.com",
            "www.wowhead.com",
        }:
            continue
        if not (since_utc <= published <= until_utc):
            continue
        searchable = f"{title}\n{summary}".casefold()
        if lowered_keywords and not any(term in searchable for term in lowered_keywords):
            continue
        output.append(NewsItem(title, link, published, summary))

    output.sort(key=lambda item: (item.published_at, item.title.casefold()), reverse=True)
    return output[: max(0, max_items)]


class WowheadNewsClient:
    def __init__(
        self,
        feed_url: str = DEFAULT_WOWHEAD_FEED,
        *,
        keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
        timeout_seconds: float = 12,
    ) -> None:
        parsed = urlparse(feed_url)
        if parsed.scheme != "https" or parsed.hostname not in {"wowhead.com", "www.wowhead.com"}:
            raise ValueError("Wowhead feed URL must use HTTPS on wowhead.com")
        self.feed_url = feed_url
        self.keywords = keywords
        self.timeout_seconds = timeout_seconds
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "WoWForeverBot/1.4 (+Discord daily report)"},
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch(
        self,
        *,
        since: datetime,
        until: datetime,
        max_items: int = 5,
    ) -> list[NewsItem]:
        await self.start()
        assert self._session is not None
        try:
            async with self._session.get(self.feed_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Wowhead RSS returned HTTP {response.status}")
                body = await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise RuntimeError("Wowhead RSS could not be retrieved") from exc
        return parse_wowhead_rss(
            body,
            since=since,
            until=until,
            keywords=self.keywords,
            max_items=max_items,
        )
