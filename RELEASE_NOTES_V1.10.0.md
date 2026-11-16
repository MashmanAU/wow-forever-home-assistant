# WoW Forever Level Bot v1.10.0

## Split-image Components V2

Version 1.10.0 adds `split_image`, a selectable production delivery mode designed to work around Discord shrinking one tall 18-character attachment.

- The corrected v1.9.2 Minimal Image is rendered once at 540 px wide.
- The output is divided into fixed groups of five rows without rescaling or changing typography.
- The current 18-character roster produces four PNGs containing ranks 1–5, 6–10, 11–15 and 16–18.
- Each PNG is attached through its own one-item Components V2 Media Gallery. The galleries are stacked vertically rather than combined into a grid.
- Commentary is placed in a Components V2 Text Display above the images.
- Scheduled `@everyone` delivery retains its explicit allowed-mentions policy.
- Wowhead news remains a separate native embed after the leaderboard when matching news exists.

## Safety and fallback

- Discord's 10-attachment message limit is checked before delivery.
- Rendering, component construction or send failure activates the existing native text/embed fallback.
- Scheduled reports and `/daily-live-test` call the exact same delivery method.
- `/daily-live-test` remains locked to `#bot-stuff`, mention-free and read-only.
- No AI model generates or edits names, levels, movement, deaths, icons or layout.

## Configuration

Set **Leaderboard render mode** to `split_image`, save the Home Assistant app configuration, restart the app and run `/daily-live-test`.

`minimal_image` remains the default until the real Discord test confirms that the shorter image blocks are materially larger and easier to read inline.

## Preserved behaviour

- Existing `minimal_image`, `table`, `native_embed`, `components_v2` and detailed `image` modes.
- Correct Alpine DejaVu font resolution and fail-loud font handling.
- Display levels without `/60`.
- Live Blizzard retrieval, snapshots, OpenAI commentary, filtered Wowhead RSS, schedules and production mentions.
- GitHub Actions tests and multi-architecture GHCR publishing.
- Corrected one-command `publish.ps1` workflow.

## Database

No schema migration is required. `/data/wow_forever.db` is unchanged.
