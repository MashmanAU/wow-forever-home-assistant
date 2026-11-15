# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.8.0

- Restores Home Assistant controls for render mode, density and displayed fields.
- Adds three factual leaderboard modes: improved native embed, Discord Components V2 and deterministic Pillow image.
- Defaults to a two-column image with class-coloured names and graphical level bars.
- Keeps announcer commentary as normal Discord message text.
- Uses the same delivery path for scheduled reports and `/daily-live-test`.
- Falls back to the native text embed if image or Components V2 delivery fails.
- Preserves live Blizzard data, snapshot history, OpenAI commentary, Wowhead RSS, scheduling and `@everyone` behaviour.

See `prototypes/COMPARISON.md` for the 18-character real-data comparison and `DEPLOY_V1.8.0.md` for the safe GitHub/GHCR update procedure.
