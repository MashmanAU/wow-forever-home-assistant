# WoW Forever Level Bot v1.9.1

## Outcome

v1.9.1 refines the Minimal Image after review of the v1.9.0 Discord output. It is substantially closer to the supplied simple reference and removes the displayed `/60` level-cap suffix from every leaderboard presentation mode.

## Minimal Image refinement

- Canvas reduced from 760 × 1,220 px to **660 × 872 px** for the supplied 18-character roster.
- Default row height reduced from 58 px plus gaps to **48 px edge-to-edge rows**.
- Removed the decorative title/date header and large rounded per-character cards.
- Replaced cards with flat alternating row bands and a one-pixel separator.
- Retained a large 44 px deterministic class glyph.
- Increased and condensed character-name typography to a heavy **34 px** font.
- Increased level typography to **25 px** and 24-hour movement to **24 px**.
- Keeps the required primary reading order: class glyph, level, 24-hour movement, character name, optional lifetime deaths.
- Rank remains off by default because row order conveys position.
- Race/class text, professions, seven-day movement, level progress and notable activity remain off the primary row by default but are still configurable. Enabling any of them expands the row to a secondary line.

## Level display change

Displayed levels are now the level only:

```text
43
Lv 43
```

The previous `43/60` and `Lv 43/60` forms are removed from:

- Minimal Image;
- native Table;
- Native Embed;
- Components V2; and
- the detailed/current Image mode.

Level 60 remains internal for progress-bar and percentage calculations.

## Native Table preserved

The Table mode remains Unicode-width aware, mobile-conscious and dependency-light. Its order is unchanged:

```text
Character  Level  24h  7d  Deaths  Details
```

The 7d and Details columns appear only when enabled. `-` continues to mean no change or no available optional value.

## Preserved behaviour

- All five selectable presentation modes and Home Assistant display controls.
- Live Blizzard data and persistent SQLite snapshot history.
- OpenAI commentary and filtered Wowhead RSS.
- Daily schedules and production `@everyone`.
- Mention-free, read-only `/daily-live-test` using the production sender.
- Native embed fallback for image, Components V2 or table failures.
- GitHub test and multi-architecture GHCR workflows.
- No database schema change.

## One-command publishing

- Adds `publish.ps1` to the repository for future releases.
- Adds a bootstrap copy at the root of the v1.9.1 review package so this release can be published directly from the extracted package.
- The normal future command is `./publish.ps1 <release-zip>` from the clean `main` clone.
- The script verifies safe ZIP paths, the SHA-256 manifest, repository structure and matching release versions.
- It blocks common credential, private-key, database, runtime-data and build-cache files before copying.
- It fast-forwards from `origin/main`, copies the release, removes obsolete tracked files, validates the diff, commits using the detected version and pushes to GitHub.
- `-NoPush` is available for a local commit-only validation run.
- The Test workflow now parses `publish.ps1` with PowerShell's own language parser before a release can pass CI.
- Git progress and informational output written to stderr, including `From https://github.com/...`, is retained without being treated as a failure. Git commands fail only on a disallowed non-zero process exit code, and genuine Git errors remain visible in the failure message.
- The Test workflow exercises both a successful fetch that writes informational stderr and a genuine failing Git command.
