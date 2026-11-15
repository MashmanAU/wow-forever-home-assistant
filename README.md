# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.9.0

- Adds a narrow `minimal_image` mode with large class glyphs, level badges, adjacent 24-hour movement and class-coloured names.
- Adds a Python-native `table` mode with Unicode-width alignment, mobile-conscious sizing and `-` for no change.
- Preserves the existing native embed, Components V2 and detailed image modes plus every Home Assistant display control.
- Defaults new installations to the simplified minimal image fields; existing installations retain saved options.
- Keeps announcer commentary as normal Discord message text.
- Uses the same delivery path for scheduled reports and `/daily-live-test`.
- Falls back to the native text embed if either image renderer or Components V2 delivery fails.
- Preserves live Blizzard data, snapshot history, OpenAI commentary, Wowhead RSS, scheduling and `@everyone` behaviour.

See `prototypes/COMPARISON.md` for the five-mode comparison and `DEPLOY_V1.9.0.md` for the safe GitHub/GHCR update procedure.
