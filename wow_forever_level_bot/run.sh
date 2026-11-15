#!/usr/bin/with-contenv bashio
set -euo pipefail

bashio::log.info "Starting WoW Forever Level Bot"
bashio::log.info "The SQLite database is stored persistently at /data/wow_forever.db"

export DISCORD_TOKEN="$(bashio::config 'discord_token')"
export BLIZZARD_CLIENT_ID="$(bashio::config 'blizzard_client_id')"
export BLIZZARD_CLIENT_SECRET="$(bashio::config 'blizzard_client_secret')"
export LOG_LEVEL="$(bashio::config 'log_level')"
export SCHEDULE_CHECK_SECONDS="$(bashio::config 'schedule_check_seconds')"
export DEFAULT_TIMEZONE="$(bashio::config 'default_timezone')"
export OPENAI_API_KEY="$(bashio::config 'openai_api_key')"
export OPENAI_MODEL="$(bashio::config 'openai_model')"
export COMMENTARY_ENABLED="$(bashio::config 'commentary_enabled')"
export COMMENTARY_MAX_WORDS="$(bashio::config 'commentary_max_words')"
export COMMENTARY_ROAST_LEVEL="$(bashio::config 'commentary_roast_level')"
export ANNOUNCER_STYLE="$(bashio::config 'announcer_style')"
export ANNOUNCER_CUSTOM_NOTES="$(bashio::config 'announcer_custom_notes')"
export COMMENTARY_NEWS_EMPHASIS="$(bashio::config 'commentary_news_emphasis')"
export COMMENTARY_CHARACTER_BANTER="$(bashio::config 'commentary_character_banter')"
export WOWHEAD_FEED_URL="$(bashio::config 'wowhead_feed_url')"
export WOWHEAD_LOOKBACK_HOURS="$(bashio::config 'wowhead_lookback_hours')"
export WOWHEAD_KEYWORDS="$(bashio::config 'wowhead_keywords')"
export TEST_CHANNEL_NAME="$(bashio::config 'test_channel_name')"
export DATABASE_PATH="/data/wow_forever.db"

exec python3 -m wow_forever_bot
