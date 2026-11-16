# WoW Forever Level Bot — Home Assistant app

A Discord bot that verifies and tracks World of Warcraft: Forever characters through Blizzard's profile API. It supports separate tracking lists and schedules for each Discord server and stores data persistently in SQLite under `/data/wow_forever.db`.

## Version 1.12.0 class icons and announcer reset

Version 1.12.0 keeps the proven v1.11.0 presentation and configuration while improving the two agreed areas:

- the Split Image renderer uses the complete 64×64 PNG Classic class-icon set from `orourkek/Wow-Icons` for Druid, Hunter, Mage, Paladin, Priest, Rogue, Shaman, Warlock and Warrior;
- the icon source is pinned to commit `5d9ad053876920138f68d69a4197fc18771b9505`, validated during the container build and distributed under the included Unlicense notice;
- the running bot never downloads artwork: GitHub Actions vendors the assets into the container and the renderer falls back to its deterministic glyph if a local icon is missing or invalid;
- story selection now asks what is genuinely most significant, novel within today's verified facts and entertaining, without preferring or penalising any category;
- significant levelling can lead on consecutive days when it remains the real story;
- anti-repetition applies to language, framing, jokes and sentence structure rather than suppressing a repeated factual topic;
- `announcer_style`, `announcer_custom_notes`, news emphasis and character banter remain editable style controls, while grounding and output limits remain code-owned;
- Split Image and Table remain the only selectable modes, `split_image_rows` remains 2–12 with a default of `6`, and the configured private test-channel behaviour is unchanged; and
- no database schema migration is required.

The image renderer is deterministic Python/Pillow code. No generative image model touches names, levels, professions or other live statistics. Missing optional data is omitted cleanly, and a missing scalable font or failed Components V2 delivery activates the native text fallback.

## Snapshot model

Every successful tracked-character refresh now stores a normalised snapshot. The bot requests only the source documents needed for the agreed model:

- base profile: level, XP, average/equipped item level, last login and character context;
- achievements: IDs, names and completion timestamps;
- achievement statistics: general lifetime deaths and selected death categories;
- PvP summary: honourable kills; and
- professions: stable profession/tier IDs and skill points.

Raw Blizzard responses, OAuth tokens and credentials are not written to the database. Optional endpoint failures produce a partial snapshot while the core level refresh continues.

The model can deterministically derive:

- levels gained over 24 hours and seven days;
- leaderboard position and 24-hour movement;
- days since the last observed level gain;
- deaths and selected death-category changes over 24 hours;
- new achievements and honourable kills;
- item-level changes; and
- profession skill gains.

Daily deltas require a baseline between 24 and 48 hours old. Weekly deltas require a baseline between seven and eight days old. Until enough history exists, the relevant values remain unknown rather than being reported as zero. Rank movement is calculated only when every currently ranked character has a valid 24-hour baseline.

### Death-counter rule

The Forever API can return more than one field labelled `Total deaths`. The snapshot model prefers the stable general statistic ID observed by the diagnostic, then the general `Death Statistics` category, and otherwise requires a single unambiguous top-level candidate. It never selects an array index such as `categories[3]`; matching uses category/statistic names and IDs. Falling, drowning, fire/lava, PvP and dungeon/raid counters are retained separately.

## Commands

- `/character-add` — verifies, adds and creates the first snapshot for a character. Available to all server members.
- `/character-remove` — removes a tracked character and its snapshot history. Requires **Manage Server**.
- `/characters` — shows cached levels, highest to lowest.
- `/level` — looks up one character without tracking or snapshotting it.
- `/levels` — refreshes all tracked characters, stores snapshots and reports highest to lowest.
- `/daily-preview` — privately renders one of five deterministic synthetic daily reports. It never reads the live database.
- `/daily-post-test` — posts synthetic character facts with live filtered Wowhead RSS and configured OpenAI commentary to the channel named by `test_channel_name`. Requires **Manage Server**, never sends a mention and never reads the live database.
- `/daily-live-test` — posts a fully real, read-only dress rehearsal to the channel named by `test_channel_name`. Requires **Manage Server**. It aborts without posting if any tracked character's live Blizzard request fails and never writes snapshots, commentary history or schedules.
- `/schedule` — posts a daily report at a nominated local time, stores snapshots and sends `@everyone`. Requires **Manage Server**.
- `/schedule-off` — disables the daily report. Requires **Manage Server**.

## Daily schedule

Use `/schedule` with:

- `channel` — report destination;
- `time` — 24-hour `HH:MM`, such as `20:30`; and
- `timezone` — IANA timezone, such as `Australia/Sydney` (default).

The schedule is stored as local wall-clock time and recalculated after each run, so daylight-saving changes do not move an 8:30 pm schedule. Running `/schedule` again replaces the server's existing schedule.

The scheduled post uses both `content="@everyone"` and an explicit Discord allowed-mentions policy. Discord will only deliver the alert if the bot role has **Mention @everyone, @here and All Roles** in the destination channel. `/schedule` checks this permission before saving.

## Required Discord permissions

- View Channels
- Send Messages
- Embed Links
- Attach Files (for `split_image`; the bot falls back to the native embed if unavailable)
- Read Message History
- Use Application Commands
- Mention @everyone, @here and All Roles

Do not grant Administrator.

## Configuration

Home Assistant exposes these options:

- `discord_token`
- `blizzard_client_id`
- `blizzard_client_secret`
- `log_level` (default `INFO`)
- `schedule_check_seconds` (default `60`)
- `default_timezone` (default `Australia/Sydney`)
- `openai_api_key` (blank uses the deterministic fallback writer)
- `openai_model` (default `gpt-4.1-mini`)
- `commentary_enabled` (default `true`)
- `commentary_max_words` (40–160; default `70`; the 75-word runtime ceiling remains in force so older saved values remain valid)
- `commentary_roast_level` (`gentle`, `mild` or `spicy`)
- `announcer_style` (editable overall voice; default retains the Azeroth sports-desk style)
- `announcer_custom_notes` (optional tone refinements; the default explicitly recognises significant levelling as valid news)
- `commentary_news_emphasis` (`low`, `normal` or `high`)
- `commentary_character_banter` (`low`, `normal` or `high`)
- `wowhead_feed_url` (must be HTTPS on `wowhead.com`)
- `wowhead_lookback_hours` (1–72; default `24`)
- `wowhead_keywords` (comma-separated exact topic filter)
- `test_channel_name` (default `bot-stuff`; used by both public test commands)
- `leaderboard_render_mode` (`split_image` or `table`; default `split_image`)
- `split_image_rows` (2–12; default `6`)
- `show_rank`, `show_race`, `show_class`, `show_level` and `show_level_progress`
- `show_lifetime_deaths`, `show_professions`, `show_24h_changes`, `show_7d_changes` and `show_notable_activity`
- `use_class_colours`, `show_class_icons` and `show_profession_icons`

## Database upgrade

Version 1.12.0 makes no database schema change. It keeps the v1.6.0 `characters`, `schedules`, `character_snapshots` and `commentary_history` tables unchanged. The newest 30 scheduled intros per guild are retained for anti-repetition; at most five are sent as style memory. `/daily-live-test` reads existing snapshots and commentary memory but keeps newly fetched Blizzard snapshots in memory and performs no database writes.

## Forever API notes

- Characters generally become visible from level 10.
- Profiles normally update after the character logs out.
- Americas and Oceania use region `us`.
- Blizzard has not formally documented the Forever namespace and may change it.

## Troubleshooting

- `@everyone` appears as plain text: grant the bot role **Mention @everyone, @here and All Roles** in the report channel, then rerun `/schedule`.
- A snapshot is partial: check the app log for the specific optional endpoint; the level can still be current.
- AI commentary uses the fallback writer: confirm the OpenAI key/model and inspect the app log. The factual report remains valid.
- No Wowhead headlines appear: no item may have matched the configured time window and Forever keywords; this is not an error.
- Test post is refused: ensure exactly one text channel matches `test_channel_name` (default `bot-stuff`) and the bot can view, send, embed and attach there.
- Live test is refused: check the same private test-channel requirements and confirm every tracked character can be fetched from Blizzard.
- Character not found: verify spelling, region, level and that the character logged out recently.
- App does not start: inspect the Home Assistant app log; credentials are never written to the log by this package.
