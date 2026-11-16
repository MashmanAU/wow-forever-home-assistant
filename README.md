# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.11.0

- Keeps the proven split-image Components V2 presentation and the monospaced Table mode; removes the four superseded selectable render modes.
- Adds `split_image_rows` in Home Assistant (2–12, default `6`) so each PNG can show more or fewer character rows.
- Makes `test_channel_name` the single destination for both `/daily-post-test` and `/daily-live-test`; both commands suppress mentions and never alter the production schedule channel.
- Removes the no-longer-needed `leaderboard_density`, `image_columns` and `image_theme` settings and fixes the retained layouts to their proven standard/dark presentation.
- Preserves field-level display controls that still affect Split Image or Table output.
- Preserves tracked characters, SQLite history, schedules, OpenAI commentary, Wowhead RSS, read-only live-test safeguards, GitHub Actions/GHCR delivery and the corrected one-command `publish.ps1`.
- Makes no database schema change and creates no migration backup.

See `RELEASE_NOTES_V1.11.0.md`, `PUBLISHING.md` and `DEPLOY_V1.11.0.md`.
