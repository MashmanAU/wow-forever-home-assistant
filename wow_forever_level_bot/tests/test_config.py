import pytest

from wow_forever_bot.config import Settings


def _credentials(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "discord")
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", "id")
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", "secret")


def test_settings_require_credentials(monkeypatch) -> None:
    for name in ("DISCORD_TOKEN", "BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="Missing"):
        Settings.from_env()


def test_settings_defaults(monkeypatch) -> None:
    _credentials(monkeypatch)
    settings = Settings.from_env()
    assert settings.default_timezone == "Australia/Sydney"
    assert settings.schedule_check_seconds == 60
    assert settings.leaderboard_render_mode == "split_image"
    assert settings.split_image_rows == 6
    assert settings.show_7d_changes is False
    assert settings.show_race is False
    assert settings.show_professions is False
    assert settings.show_notable_activity is False
    assert settings.daily_notification == "everyone"


def test_ai_and_preview_defaults(monkeypatch) -> None:
    _credentials(monkeypatch)
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
    _credentials(monkeypatch)
    monkeypatch.setenv("ANNOUNCER_STYLE", "Deadpan auction-house desk.")
    monkeypatch.setenv("ANNOUNCER_CUSTOM_NOTES", "No catchphrases.")
    monkeypatch.setenv("COMMENTARY_NEWS_EMPHASIS", "high")
    monkeypatch.setenv("COMMENTARY_CHARACTER_BANTER", "low")
    settings = Settings.from_env()
    assert settings.announcer_style == "Deadpan auction-house desk."
    assert settings.announcer_custom_notes == "No catchphrases."
    assert settings.commentary_news_emphasis == "high"
    assert settings.commentary_character_banter == "low"


def test_retained_display_settings_are_configurable(monkeypatch) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("LEADERBOARD_RENDER_MODE", "table")
    monkeypatch.setenv("SPLIT_IMAGE_ROWS", "8")
    monkeypatch.setenv("SHOW_PROFESSIONS", "false")
    monkeypatch.setenv("SHOW_7D_CHANGES", "true")
    settings = Settings.from_env()
    assert settings.leaderboard_render_mode == "table"
    assert settings.split_image_rows == 8
    assert settings.show_professions is False
    assert settings.show_7d_changes is True


@pytest.mark.parametrize("value", ("everyone", "here", "none"))
def test_daily_notification_options_are_configurable(monkeypatch, value: str) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("DAILY_NOTIFICATION", value)
    assert Settings.from_env().daily_notification == value


def test_invalid_daily_notification_is_rejected(monkeypatch) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("DAILY_NOTIFICATION", "channel")
    with pytest.raises(RuntimeError, match="everyone, here or none"):
        Settings.from_env()


@pytest.mark.parametrize("mode", ("split_image", "table"))
def test_retained_render_modes_are_selectable(monkeypatch, mode: str) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("LEADERBOARD_RENDER_MODE", mode)
    assert Settings.from_env().leaderboard_render_mode == mode


@pytest.mark.parametrize("mode", ("minimal_image", "native_embed", "components_v2", "image"))
def test_removed_render_modes_are_rejected(monkeypatch, mode: str) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("LEADERBOARD_RENDER_MODE", mode)
    with pytest.raises(RuntimeError, match="split_image or table"):
        Settings.from_env()


@pytest.mark.parametrize("value", ("1", "13"))
def test_split_image_rows_range_is_enforced(monkeypatch, value: str) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("SPLIT_IMAGE_ROWS", value)
    with pytest.raises(RuntimeError, match="between 2 and 12"):
        Settings.from_env()


def test_removed_display_environment_values_are_ignored(monkeypatch) -> None:
    _credentials(monkeypatch)
    monkeypatch.setenv("LEADERBOARD_DENSITY", "compact")
    monkeypatch.setenv("IMAGE_COLUMNS", "one")
    monkeypatch.setenv("IMAGE_THEME", "parchment")
    settings = Settings.from_env()
    assert not hasattr(settings, "leaderboard_density")
    assert not hasattr(settings, "image_columns")
    assert not hasattr(settings, "image_theme")
