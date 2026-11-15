from pathlib import Path

from wow_forever_bot import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_and_home_assistant_build_metadata() -> None:
    assert __version__ == "1.9.1"
    config = (ROOT / "config.yaml").read_text()
    assert 'version: "1.9.1"' in config
    assert 'version = "1.9.1"' in (ROOT / "pyproject.toml").read_text()
    assert "image: ghcr.io/mashmanau/{arch}-wow-forever-level-bot" in config
    assert not (ROOT / "build.yaml").exists()


def test_authorization_headers_use_runtime_bearer_values() -> None:
    blizzard = (ROOT / "wow_forever_bot" / "blizzard.py").read_text()
    commentary = (ROOT / "wow_forever_bot" / "commentary.py").read_text()
    assert 'Bearer {token}' in blizzard
    assert 'Bearer {self.api_key}' in commentary
    assert 'character_slug(first_name, surname)' in blizzard


def test_daily_post_test_uses_hybrid_builder_and_suppresses_mentions() -> None:
    source = (ROOT / "wow_forever_bot" / "bot.py").read_text()
    command = source.split('name="daily-post-test"', 1)[1].split(
        'name="daily-live-test"', 1
    )[0]
    assert "build_fixture_live_news_bundle(" in command
    assert "build_fixture_daily_bundle(" not in command
    assert "AllowedMentions.none()" in command
    assert "@everyone" not in command
    assert "self.bot.store" not in command


def test_release_defaults_to_verified_working_openai_model() -> None:
    assert "openai_model: gpt-4.1-mini" in (ROOT / "config.yaml").read_text()
    config_source = (ROOT / "wow_forever_bot" / "config.py").read_text()
    assert 'openai_model: str = "gpt-4.1-mini"' in config_source


def test_daily_live_test_is_hard_locked_and_has_no_persistence_calls() -> None:
    source = (ROOT / "wow_forever_bot" / "bot.py").read_text()
    command = source.split('name="daily-live-test"', 1)[1].split(
        'name="schedule"', 1
    )[0]
    assert 'LIVE_TEST_CHANNEL_NAME = "bot-stuff"' in source
    assert "build_live_test_daily_bundle(" in command
    assert "build_fixture" not in command
    assert "scenario" not in command
    assert "AllowedMentions.none()" in command
    assert "@everyone" not in command
    assert "save_snapshot(" not in command
    assert "update_character(" not in command
    assert "save_commentary(" not in command
    assert "set_schedule(" not in command
    assert "self._send_daily_report(" in command
    fetch_helper = source.split("async def _fetch_live_snapshots_read_only", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert "get_snapshot(" in fetch_helper
    assert "save_snapshot(" not in fetch_helper
    assert "update_character(" not in fetch_helper


def test_personality_is_configurable_but_guardrails_remain_code_owned() -> None:
    config = (ROOT / "config.yaml").read_text()
    commentary = (ROOT / "wow_forever_bot" / "commentary.py").read_text()
    for field in (
        "announcer_style",
        "announcer_custom_notes",
        "commentary_news_emphasis",
        "commentary_character_banter",
    ):
        assert field in config
    assert "_FIXED_GROUNDING_RULES" in commentary
    assert "_FIXED_REPETITION_RULES" in commentary
    assert "_FIXED_OUTPUT_RULES" in commentary
    assert '"type": "json_schema"' in commentary
    assert "for attempt in range(2)" in commentary
    assert "_fallback(payload)" in commentary


def test_release_contains_short_radio_and_history_defaults() -> None:
    config = (ROOT / "config.yaml").read_text()
    commentary = (ROOT / "wow_forever_bot" / "commentary.py").read_text()
    store = (ROOT / "wow_forever_bot" / "store.py").read_text()
    assert "commentary_max_words: 70" in config
    assert "effective_max_words" in commentary
    assert "recent_commentary" in commentary
    assert "commentary_history" in store
    bot = (ROOT / "wow_forever_bot" / "bot.py").read_text()
    send_position = bot.index("await channel.send(")
    save_position = bot.index("await self.bot.store.save_commentary(")
    assert save_position > send_position


def test_daily_leaderboard_has_five_modes_and_native_fallback() -> None:
    source = (ROOT / "wow_forever_bot" / "bot.py").read_text()
    presentation = (ROOT / "wow_forever_bot" / "presentation.py").read_text()
    embed_renderer = source.split("def _leaderboard_embed", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert "leaderboard_description(" in embed_renderer
    assert 'title="🏆 WoW Forever leaderboard"' in embed_renderer
    assert 'return first_line + "\\n↳ "' in presentation
    assert 'mode in {"image", "minimal_image"}' in source
    assert '"minimal_image"' in source
    assert 'mode == "table"' in source
    assert 'mode == "components_v2"' in source
    assert "render_minimal_leaderboard_png" in source
    assert "leaderboard_table_code_blocks" in source
    assert "native text fallback" in source


def test_displayed_levels_omit_the_internal_level_cap() -> None:
    presentation = (ROOT / "wow_forever_bot" / "presentation.py").read_text()
    image = (ROOT / "wow_forever_bot" / "image_renderer.py").read_text()
    table = (ROOT / "wow_forever_bot" / "table_renderer.py").read_text()
    assert "snapshot.level}/60" not in presentation
    assert "snapshot.level}/60" not in image
    assert "snapshot.level}/60" not in table


def test_home_assistant_exposes_display_customisation() -> None:
    config = (ROOT / "config.yaml").read_text()
    run = (ROOT / "run.sh").read_text()
    for field in (
        "leaderboard_render_mode",
        "leaderboard_density",
        "show_rank",
        "show_race",
        "show_class",
        "show_level",
        "show_level_progress",
        "show_lifetime_deaths",
        "show_professions",
        "show_24h_changes",
        "show_7d_changes",
        "show_notable_activity",
        "image_columns",
        "image_theme",
        "use_class_colours",
        "show_class_icons",
        "show_profession_icons",
    ):
        assert field in config
        assert field.upper() in run


def test_schedule_and_live_test_share_the_exact_delivery_method() -> None:
    source = (ROOT / "wow_forever_bot" / "bot.py").read_text()
    schedule_worker = source.split("async def schedule_worker", 1)[1].split(
        "@schedule_worker.before_loop", 1
    )[0]
    live_test = source.split('name="daily-live-test"', 1)[1].split(
        'name="schedule"', 1
    )[0]
    assert "self._send_daily_report(" in schedule_worker
    assert "self._send_daily_report(" in live_test


def test_daily_commentary_is_plain_message_text_without_public_debug_footers() -> None:
    source = (ROOT / "wow_forever_bot" / "bot.py").read_text()
    presentation = (ROOT / "wow_forever_bot" / "presentation.py").read_text()
    delivery = source.split("async def _send_daily_report", 1)[1].split(
        "@tasks.loop", 1
    )[0]
    assert "bundle.commentary.text" in presentation
    assert "bundle.commentary.text" not in delivery
    assert "normal Discord message" in delivery
    assert "set_footer" not in delivery
    assert "_news_embed(bundle)" in delivery
