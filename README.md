# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.12.0

- Replaces the generated class glyphs for the nine WoW Forever classes with the 64×64 PNG set from `orourkek/Wow-Icons`.
- Pins icon retrieval to commit `5d9ad053876920138f68d69a4197fc18771b9505`, validates each asset during the container build and ships the Unlicense notice.
- Keeps asset retrieval in the build only: the running app uses local container files and retains the deterministic glyph as a defensive fallback.
- Resets announcer editorial selection so levelling, rankings, deaths, achievements, professions, gear, PvP, XP, inactivity and supplied news are equally eligible.
- Makes the current day's significance the lead criterion and applies anti-repetition to wording, framing, jokes and sentence structure rather than suppressing a repeated real topic.
- Preserves the v1.11.0 Split Image/Table configuration, private test-channel fix, tracked data, schedules, Wowhead filtering, read-only safeguards and corrected one-command `publish.ps1`.
- Makes no database schema change and creates no migration backup.

See `RELEASE_NOTES_V1.12.0.md`, `PUBLISHING.md` and `DEPLOY_V1.12.0.md`.
