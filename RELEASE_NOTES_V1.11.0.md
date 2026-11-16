# WoW Forever Level Bot v1.11.0

## Outcome

v1.11.0 simplifies Home Assistant configuration around the two retained presentation choices: Split Image and Table.

## Changes

- Adds `split_image_rows` with a range of 2–12 and a default of 6.
- Uses that value for both PNG chunking and Components V2 accessibility rank descriptions.
- Makes `split_image` the default render mode and restricts selectable modes to `split_image` and `table`.
- Removes `leaderboard_density`, `image_columns` and `image_theme` from Home Assistant, startup exports and runtime settings.
- Removes the superseded detailed Image and native Components V2 production branches; Native Embed remains a defensive fallback.
- Uses the fixed proven dark style and fixed standard Table width/profession limits.
- Resolves both `/daily-post-test` and `/daily-live-test` from `test_channel_name`, requiring exactly one matching text channel.
- Keeps both test commands mention-free. The production scheduler still uses its persisted `schedule.channel_id` and retains `@everyone` behaviour.

## Preserved without migration

- Existing character rows and SQLite snapshot/commentary history.
- Stored production schedules and next-run calculation.
- Read-only `/daily-live-test` boundaries.
- OpenAI commentary, deterministic fallback and style history.
- Wowhead RSS filtering.
- GitHub Actions, multi-architecture GHCR builds and Home Assistant repository delivery.
- Corrected one-command `publish.ps1` and its integration checks.

There is no database schema change and no backup step is required for this release.
