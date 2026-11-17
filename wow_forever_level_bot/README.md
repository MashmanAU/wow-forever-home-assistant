# WoW Forever Level Bot — Home Assistant app

A Discord bot that verifies and tracks World of Warcraft: Forever characters through Blizzard's profile API. It supports separate tracking lists and schedules for each Discord server and stores data persistently in SQLite under `/data/wow_forever.db`.

## Version 1.14.0 accurate daily movement and scale-aware commentary

Version 1.14.0 corrects daily movement and balances commentary while retaining the v1.13.0 presentation, notifications, class icons and announcer behaviour:

- 24-hour changes use the stored snapshot nearest the intended 24-hour mark, tolerating normal scheduler jitter and daylight-saving changes;
- a slightly early daily run no longer skips yesterday's snapshot and compares against the day before;
- a missing suitable baseline is shown as unknown instead of being stretched into an inaccurate daily value;
- commentary significance normalises profession gains against their 150–300 point scale;
- character levels receive substantial weighting, increasing towards the level-60 cap; and
- existing notification, read-only test, Split Image/Table and native fallback behaviour is unchanged; and
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

Daily deltas use the stored observation nearest 24 hours ago within an 18–30 hour tolerance. Weekly deltas use the observation nearest seven days ago within a ±12-hour tolerance. These symmetric windows prevent normal scheduling jitter from accidentally selecting a two-day-old baseline. Until a suitable baseline exists, the relevant values remain unknown rather than being reported as zero. Rank movement is calculated only when every currently ranked character has a valid 24-hour baseline.

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
- `/schedule` — posts a daily report at a nominated local time, stores snapshots and uses the configured daily notification. Requires **Manage Server**.
- `/schedule-off` — disables the daily report. Requires **Manage Server**.

## Daily schedule

Use `/schedule` with:

- `channel` — report destination;
- `time` — 24-hour `HH:MM`, such as `20:30`; and
- `timezone` — IANA timezone, such as `Australia/Sydney` (default).

The schedule is stored as local wall-clock time and recalculated after each run, so daylight-saving changes do not move an 8:30 pm schedule. Running `/schedule` again replaces the server's existing schedule.

Scheduled posts use the `daily_notification` setting: `everyone` sends `@everyone`, `here` sends `@here`, and `none` sends no mention. The default is `everyone`. Discord will only deliver either mention if the bot role has **Mention @everyone, @here and All Roles** in the destination channel. `/schedule` checks that permission when either notifying option is selected. Changing the setting requires Save + Restart only; the existing schedule remains valid.

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
- `wowhead_keywords` (optional comma-separated exact topic filter; blank disables keyword filtering)
- `daily_notification` (`everyone`, `here` or `none`; default `everyone`)
- `test_channel_name` (default `bot-stuff`; used by both public test commands)
- `leaderboard_render_mode` (`split_image` or `table`; default `split_image`)
- `split_image_rows` (2–12; default `6`)
- `show_rank`, `show_race`, `show_class`, `show_level` and `show_level_progress`
- `show_lifetime_deaths`, `show_professions`, `show_24h_changes`, `show_7d_changes` and `show_notable_activity`
- `use_class_colours`, `show_class_icons` and `show_profession_icons`

## Database upgrade

Version 1.14.0 makes no database schema change. It keeps the v1.6.0 `characters`, `schedules`, `character_snapshots` and `commentary_history` tables unchanged. The notification choice remains global Home Assistant app configuration, not schedule data. The newest 30 scheduled intros per guild are retained for anti-repetition; at most five are sent as style memory. `/daily-live-test` reads existing snapshots and commentary memory but keeps newly fetched Blizzard snapshots in memory and performs no database writes.

## Forever API notes

- Characters generally become visible from level 10.
- Profiles normally update after the character logs out.
- Americas and Oceania use region `us`.
- Blizzard has not formally documented the Forever namespace and may change it.

## Troubleshooting

- `@everyone` or `@here` appears as plain text: grant the bot role **Mention @everyone, @here and All Roles** in the report channel, then confirm the configured daily notification. Rerunning `/schedule` is required only if the destination or time also needs to change.
- A snapshot is partial: check the app log for the specific optional endpoint; the level can still be current.
- AI commentary uses the fallback writer: confirm the OpenAI key/model and inspect the app log. The factual report remains valid.
- No Wowhead headlines appear: no item may have matched the configured time window and Forever keywords; this is not an error.
- Test post is refused: ensure exactly one text channel matches `test_channel_name` (default `bot-stuff`) and the bot can view, send, embed and attach there.
- Live test is refused: check the same private test-channel requirements and confirm every tracked character can be fetched from Blizzard.
- Character not found: verify spelling, region, level and that the character logged out recently.
- App does not start: inspect the Home Assistant app log; credentials are never written to the log by this package.
