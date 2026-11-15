# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.9.1

- Refines `minimal_image` to a 660 px flat-row layout closely matching the supplied simple reference, with substantially larger/heavier names and tighter vertical density.
- Keeps the level badge and larger 24-hour movement adjacent, with optional deaths at the far right.
- Removes the displayed `/60` suffix from levels in every leaderboard presentation while retaining level 60 internally for progress calculations.
- Preserves the Python-native `table` mode with Unicode-width alignment, Character → Level → 24h → optional 7d → Deaths ordering and `-` for no change.
- Preserves the existing native embed, Components V2 and detailed image modes plus every Home Assistant display control.
- Defaults new installations to the simplified minimal image fields; existing installations retain saved options.
- Keeps announcer commentary as normal Discord message text.
- Uses the same delivery path for scheduled reports and `/daily-live-test`.
- Falls back to the native text embed if either image renderer or Components V2 delivery fails.
- Preserves live Blizzard data, snapshot history, OpenAI commentary, Wowhead RSS, scheduling and `@everyone` behaviour.
- Adds a guarded one-command `publish.ps1` release workflow with package checksum, version and sensitive-file validation.

See `prototypes/COMPARISON.md` for the five-mode comparison, `PUBLISHING.md` for the one-command workflow and `DEPLOY_V1.9.1.md` for the safe GitHub/GHCR update procedure.
