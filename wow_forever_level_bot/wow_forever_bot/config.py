from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_ANNOUNCER_STYLE = (
    "Cheeky Azeroth sports desk and radio announcer with dry humour, short sharp observations "
    "and light roasting. Sound like you are talking to a group of mates who play WoW "
    "together. Avoid motivational newsletter language."
)
DEFAULT_ANNOUNCER_CUSTOM_NOTES = (
    "Cold opens are encouraged. WoW references are welcome but do not force them. "
    "Occasional running jokes are fine. Do not finish every report with a catchphrase."
)


def _boolean_env(name: str, default: bool) -> bool:
    value = os.getenv(name, "true" if default else "false").strip().lower()
    if value not in {"true", "false"}:
        raise RuntimeError(f"{name} must be true or false")
    return value == "true"


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    blizzard_client_id: str
    blizzard_client_secret: str
    database_path: str = "/data/wow_forever.db"
    schedule_check_seconds: int = 60
    default_timezone: str = "Australia/Sydney"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    commentary_enabled: bool = True
    commentary_max_words: int = 70
    commentary_roast_level: str = "mild"
    announcer_style: str = DEFAULT_ANNOUNCER_STYLE
    announcer_custom_notes: str = DEFAULT_ANNOUNCER_CUSTOM_NOTES
    commentary_news_emphasis: str = "normal"
    commentary_character_banter: str = "normal"
    wowhead_feed_url: str = "https://www.wowhead.com/news/rss/all"
    wowhead_lookback_hours: int = 24
    wowhead_keywords: tuple[str, ...] = (
        "wow forever",
        "world of warcraft forever",
        "forever realms",
        "forever realm",
        "forever hardcore",
    )
    test_channel_name: str = "bot-stuff"

    @classmethod
    def from_env(cls) -> "Settings":
        required = {
            "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN", "").strip(),
            "BLIZZARD_CLIENT_ID": os.getenv("BLIZZARD_CLIENT_ID", "").strip(),
            "BLIZZARD_CLIENT_SECRET": os.getenv("BLIZZARD_CLIENT_SECRET", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

        seconds = int(os.getenv("SCHEDULE_CHECK_SECONDS", "60"))
        if not 15 <= seconds <= 3600:
            raise RuntimeError("SCHEDULE_CHECK_SECONDS must be between 15 and 3600")

        max_words = int(os.getenv("COMMENTARY_MAX_WORDS", "70"))
        if not 40 <= max_words <= 160:
            raise RuntimeError("COMMENTARY_MAX_WORDS must be between 40 and 160")
        lookback = int(os.getenv("WOWHEAD_LOOKBACK_HOURS", "24"))
        if not 1 <= lookback <= 72:
            raise RuntimeError("WOWHEAD_LOOKBACK_HOURS must be between 1 and 72")
        roast_level = os.getenv("COMMENTARY_ROAST_LEVEL", "mild").strip().lower()
        if roast_level not in {"gentle", "mild", "spicy"}:
            raise RuntimeError("COMMENTARY_ROAST_LEVEL must be gentle, mild or spicy")
        news_emphasis = os.getenv("COMMENTARY_NEWS_EMPHASIS", "normal").strip().lower()
        if news_emphasis not in {"low", "normal", "high"}:
            raise RuntimeError("COMMENTARY_NEWS_EMPHASIS must be low, normal or high")
        character_banter = os.getenv("COMMENTARY_CHARACTER_BANTER", "normal").strip().lower()
        if character_banter not in {"low", "normal", "high"}:
            raise RuntimeError("COMMENTARY_CHARACTER_BANTER must be low, normal or high")
        keywords = tuple(
            item.strip()
            for item in os.getenv(
                "WOWHEAD_KEYWORDS",
                "wow forever,world of warcraft forever,forever realms,forever realm,forever hardcore",
            ).split(",")
            if item.strip()
        )
        return cls(
            discord_token=required["DISCORD_TOKEN"],
            blizzard_client_id=required["BLIZZARD_CLIENT_ID"],
            blizzard_client_secret=required["BLIZZARD_CLIENT_SECRET"],
            database_path=os.getenv("DATABASE_PATH", "/data/wow_forever.db"),
            schedule_check_seconds=seconds,
            default_timezone=os.getenv("DEFAULT_TIMEZONE", "Australia/Sydney").strip()
            or "Australia/Sydney",
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
            commentary_enabled=_boolean_env("COMMENTARY_ENABLED", True),
            commentary_max_words=max_words,
            commentary_roast_level=roast_level,
            announcer_style=os.getenv(
                "ANNOUNCER_STYLE",
                DEFAULT_ANNOUNCER_STYLE,
            ).strip()
            or DEFAULT_ANNOUNCER_STYLE,
            announcer_custom_notes=os.getenv(
                "ANNOUNCER_CUSTOM_NOTES",
                DEFAULT_ANNOUNCER_CUSTOM_NOTES,
            ).strip(),
            commentary_news_emphasis=news_emphasis,
            commentary_character_banter=character_banter,
            wowhead_feed_url=os.getenv(
                "WOWHEAD_FEED_URL", "https://www.wowhead.com/news/rss/all"
            ).strip(),
            wowhead_lookback_hours=lookback,
            wowhead_keywords=keywords,
            test_channel_name=os.getenv("TEST_CHANNEL_NAME", "bot-stuff").strip()
            or "bot-stuff",
        )
