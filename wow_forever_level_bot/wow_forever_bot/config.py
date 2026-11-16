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
    leaderboard_render_mode: str = "minimal_image"
    leaderboard_density: str = "standard"
    show_rank: bool = False
    show_race: bool = False
    show_class: bool = False
    show_level: bool = True
    show_level_progress: bool = False
    show_lifetime_deaths: bool = True
    show_professions: bool = False
    show_24h_changes: bool = True
    show_7d_changes: bool = False
    show_notable_activity: bool = False
    image_columns: str = "two"
    image_theme: str = "dark_warcraft"
    use_class_colours: bool = True
    show_class_icons: bool = True
    show_profession_icons: bool = True

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
        render_mode = os.getenv("LEADERBOARD_RENDER_MODE", "minimal_image").strip().lower()
        if render_mode not in {
            "native_embed",
            "components_v2",
            "image",
            "minimal_image",
            "split_image",
            "table",
        }:
            raise RuntimeError(
                "LEADERBOARD_RENDER_MODE must be native_embed, components_v2, image, "
                "minimal_image, split_image or table"
            )
        density = os.getenv("LEADERBOARD_DENSITY", "standard").strip().lower()
        if density not in {"compact", "standard", "detailed"}:
            raise RuntimeError(
                "LEADERBOARD_DENSITY must be compact, standard or detailed"
            )
        image_columns = os.getenv("IMAGE_COLUMNS", "two").strip().lower()
        if image_columns not in {"one", "two"}:
            raise RuntimeError("IMAGE_COLUMNS must be one or two")
        image_theme = os.getenv("IMAGE_THEME", "dark_warcraft").strip().lower()
        if image_theme not in {"dark_warcraft", "parchment", "minimal"}:
            raise RuntimeError(
                "IMAGE_THEME must be dark_warcraft, parchment or minimal"
            )
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
            leaderboard_render_mode=render_mode,
            leaderboard_density=density,
            show_rank=_boolean_env("SHOW_RANK", False),
            show_race=_boolean_env("SHOW_RACE", False),
            show_class=_boolean_env("SHOW_CLASS", False),
            show_level=_boolean_env("SHOW_LEVEL", True),
            show_level_progress=_boolean_env("SHOW_LEVEL_PROGRESS", False),
            show_lifetime_deaths=_boolean_env("SHOW_LIFETIME_DEATHS", True),
            show_professions=_boolean_env("SHOW_PROFESSIONS", False),
            show_24h_changes=_boolean_env("SHOW_24H_CHANGES", True),
            show_7d_changes=_boolean_env("SHOW_7D_CHANGES", False),
            show_notable_activity=_boolean_env("SHOW_NOTABLE_ACTIVITY", False),
            image_columns=image_columns,
            image_theme=image_theme,
            use_class_colours=_boolean_env("USE_CLASS_COLOURS", True),
            show_class_icons=_boolean_env("SHOW_CLASS_ICONS", True),
            show_profession_icons=_boolean_env("SHOW_PROFESSION_ICONS", True),
        )
