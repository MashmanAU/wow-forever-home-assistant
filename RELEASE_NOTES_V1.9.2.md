# WoW Forever Level Bot v1.9.2

## Outcome

v1.9.2 fixes the actual Home Assistant-generated Minimal Image typography. The previous production container installed DejaVu fonts under `/usr/share/fonts/dejavu`, but the renderer did not search that directory and silently fell back to Pillow's tiny bitmap font. This release resolves the real Alpine path and prevents silent bitmap fallback.

## Minimal Image correction

- Canvas reduced from 660 px to **540 px** wide.
- Default rows are **54 px** high and remain one compact line.
- Deterministic class glyphs are **48 × 48 px**.
- Level badges are **46 × 46 px**, with **19 px bold** level text.
- 24-hour movement remains immediately after the level and uses **18 px bold** text.
- Character names use **27 px bold condensed** type and remain class-coloured.
- Names, levels and movement are vertically centred against the class glyph.
- Optional lifetime deaths remain aligned at the far right.
- `/60` remains absent from every displayed level.
- Explicitly enabled secondary fields remain available on an expanded second line.

## Production font safety

- Adds Alpine's real `font-dejavu` directory, `/usr/share/fonts/dejavu`, to font discovery.
- Keeps the Docker package installation unchanged.
- If no scalable font is available, image rendering now raises an error so the existing native Discord fallback is used instead of an unreadable PNG.
- Adds automated coverage for scalable-font selection and the Alpine font directory.

## Preserved behaviour

- Table, Native Embed, Components V2 and detailed Image modes.
- Every existing Home Assistant display control and saved configuration.
- Class colours, class icons and optional secondary fields.
- Live Blizzard data and persistent SQLite snapshot history.
- OpenAI commentary and filtered Wowhead RSS.
- Daily schedules, production `@everyone` and schedule advancement.
- Mention-free, read-only `/daily-live-test` using the production sender.
- GitHub tests, one-command publishing and multi-architecture GHCR builds.
- No database schema change.

## Publisher integration-test correction

- The integration test now explicitly exits `0` after both expected publisher checks pass, rather than leaking the intentionally failed child publisher's `$LASTEXITCODE` into the test process.
- Assertion and setup failures are captured, reported and explicitly exit `1` after temporary repositories are cleaned up.
- The GitHub Actions step runs the integration test in a child PowerShell process and validates both exit paths: ordinary success must return `0`, while a forced assertion failure must return non-zero and preserve its error message.
- The corrected `publish.ps1` Git stderr and exit-code behaviour is unchanged.
