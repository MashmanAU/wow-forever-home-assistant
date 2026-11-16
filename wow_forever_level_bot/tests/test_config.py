import pytest

from wow_forever_bot.config import Settings


def test_settings_require_credentials(monkeypatch) -> None:
    for name in ("DISCORD_TOKEN", "BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="Missing"):
        Settings.from_env()


def test_settings_defaults(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "discord")
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", "id")
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", "secret")
    settings = Settings.from_env()
    assert settings.default_timezone == "Australia/Sydney"
    assert settings.schedule_check_seconds == 60
    assert settings.leaderboard_render_mode == "minimal_image"
    assert settings.leaderboard_density == "standard"
    assert settings.image_columns == "two"
    assert settings.show_7d_changes is False
    assert settings.show_race is False
    assert settings.show_professions is False
    assert settings.show_notable_activity is False


def test_ai_and_preview_defaults(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "discord")
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", "id")
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", "secret")
    settings = Settings.from_env()
    assert settings.commentary_enabled is True
    assert settings.commentary_max_words == 70
    assert settings.openai_model == "gpt-4.1-mini"
    assert settings.test_channel_name == "bot-stuff"
    assert settings.wowhead_feed_url == "https://www.wowhead.com/news/rss/all"
    assert "Azeroth sports desk" in settings.announcer_style
    assert settings.commentary_news_emphasis == "normal"
    assert settings.commentary_character_banter == "normal"


def test_personality_settings_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "discord")
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", "id")
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ANNOUNCER_STYLE", "Deadpan auction-house desk.")
    monkeypatch.setenv("ANNOUNCER_CUSTOM_NOTES", "No catchphrases.")
    monkeypatch.setenv("COMMENTARY_NEWS_EMPHASIS", "high")
    monkeypatch.setenv("COMMENTARY_CHARACTER_BANTER", "low")
    settings = Settings.from_env()
    assert settings.announcer_style == "Deadpan auction-house desk."
    assert settings.announcer_custom_notes == "No catchphrases."
    assert settings.commentary_news_emphasis == "high"
    assert settings.commentary_character_banter == "low"


def test_display_settings_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "discord")
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", "id")
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", "secret")
    monkeypatch.setenv("LEADERBOARD_RENDER_MODE", "components_v2")
    monkeypatch.setenv("LEADERBOARD_DENSITY", "compact")
    monkeypatch.setenv("SHOW_PROFESSIONS", "false")
    monkeypatch.setenv("SHOW_7D_CHANGES", "true")
    monkeypatch.setenv("IMAGE_THEME", "parchment")
    settings = Settings.from_env()
    assert settings.leaderboard_render_mode == "components_v2"
    assert settings.leaderboard_density == "compact"
    assert settings.show_professions is False
    assert settings.show_7d_changes is True
    assert settings.image_theme == "parchment"


@pytest.mark.parametrize(
    "mode",
    ("minimal_image", "split_image", "table", "native_embed", "components_v2", "image"),
)
def test_every_render_mode_is_selectable(monkeypatch, mode: str) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "discord")
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", "id")
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", "secret")
    monkeypatch.setenv("LEADERBOARD_RENDER_MODE", mode)
    assert Settings.from_env().leaderboard_render_mode == mode
