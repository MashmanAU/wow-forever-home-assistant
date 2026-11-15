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
