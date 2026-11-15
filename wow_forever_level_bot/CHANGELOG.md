# Changelog

## 1.7.1

- Standardises the daily leaderboard as one embed with exactly two Discord Markdown lines per character.
- Places name, race/class and level-to-60 progress on line one.
- Places lifetime deaths, profession skill values, available deltas and relevant notable activity on line two.
- Keeps AI commentary in normal message text, removes public technical/debug footers and avoids unsupported per-character text colours.
- Omits the Wowhead section when no qualifying Forever headline exists.
- Uses the same production renderer for `/daily-live-test`, with mentions suppressed and no persistence calls.
- Preserves live Blizzard data, OpenAI, Wowhead, schedule advancement, production `@everyone`, backups and rollback.

## 1.7.0

- Adds Home Assistant `compact` and `normal` daily leaderboard layouts.
- Adds independent visibility switches for race, class, level-to-60 progress, lifetime deaths, professions, 24-hour changes, seven-day changes, ranking and notable activity.
- Renders compact character facts without empty lines or dangling separators when data or configured fields are absent.
- Moves AI announcer copy into normal Discord message text and removes public technical/debug footers.
- Omits the Wowhead section when no qualifying Forever headline exists.
- Makes `/daily-live-test` use the exact configured production renderer while retaining mention suppression and all read-only boundaries.
- Preserves scheduled `@everyone`, live Blizzard snapshots, OpenAI commentary, filtered Wowhead RSS, stored commentary memory, schedule advancement and the v1.6.0 database schema.

## 1.6.0

- Adds `/daily-live-test`, hard-locked to exactly one `#bot-stuff` channel with all Discord mentions disabled.
- Fetches current Blizzard snapshots for every tracked character, then derives real 24-hour and seven-day changes against the existing stored history without persisting the new snapshots.
- Uses live filtered Wowhead RSS, the existing `gpt-4.1-mini` OpenAI path and recent scheduled commentary memory for a production-like dress rehearsal.
- Aborts before posting if any tracked character cannot be refreshed, rather than presenting a partially stale roster as current.
- Does not update cached character rows, create snapshots, move baselines, write commentary history, alter schedules or advance the next-run value.
- Exposes announcer style, custom style notes, news emphasis and character banter through Home Assistant configuration.
- Keeps factual grounding, strict JSON schema, prompt-injection resistance, anti-repetition, one rewrite and deterministic fallback fixed in source code.
- Retains the v1.5.0 database schema, OpenAI model, schedule behaviour and source-only deployment/rollback workflow.

## 1.5.0

- Rewrites the daily voice as a 35–75 word Azeroth drive-time bulletin with punchy sentences and a dry sign-off.
- Adds deterministic story-angle selection that favours achievements, crafting, gear, PvP, leaderboard movement, XP and news over another levels/deaths recap.
- Expands the controlled AI payload with underused facts already present in snapshots, including XP, current gear/profession values, context, baseline timestamps and guild totals.
- Adds bounded per-guild commentary history, recent-copy prompt awareness, local similarity detection, one rewrite and grounded fallback after a second collision.
- Adds `crafting-day` and `pvp-night` synthetic scenarios alongside radio, quiet and comeback coverage.
- Preserves structured output, factual grounding, RSS/OpenAI fallbacks, test isolation and mention suppression.
- Retains manifest-verified preflight, source-only deployment, external backup and rollback.

## 1.4.0

- Adds OpenAI Responses API radio commentary with strict structured output and a deterministic fallback writer.
- Sends only a controlled JSON fact set; raw Blizzard payloads and Wowhead article bodies are excluded.
- Adds tightly filtered Wowhead RSS headline ingestion with HTTPS host validation and bounded lookback.
- Adds ephemeral `/daily-preview` and locked, mention-free `/daily-post-test` commands.
- Adds three fixed-clock synthetic snapshot scenarios and an offline preview CLI.
- Guards test databases against `/data/wow_forever.db` and keeps test stores schedule-free.
- Preserves factual scheduled posts when either Wowhead or OpenAI is unavailable.
- Moves upgrade backups outside `/local_apps` to prevent duplicate slug discovery.

## 1.3.0

- Adds a durable, normalised character snapshot model without storing raw Blizzard payloads.
- Captures level, XP, average/equipped item level, last login, class/race/faction/ruleset context, achievements, honourable kills, profession tiers and selected death counters.
- Uses the combined realmless character slug (for example `mash-man`) and sends the real OAuth bearer token, incorporating the live v1.2 fixes.
- Resolves lifetime deaths by the known general statistic ID, the semantic `Death Statistics` category or one unambiguous top-level candidate—never by array position. Ambiguous totals are stored as unknown instead of guessed.
- Retains falling, drowning, fire/lava, PvP and dungeon/raid lifetime counters for change-only commentary later.
- Derives deterministic 24-hour and seven-day progress, leaderboard rank/movement, new achievements, profession gains, honourable-kill changes, item-level changes and days since the last observed level gain.
- Requires an appropriately aged baseline (24–48 hours for daily deltas; seven–eight days for weekly deltas), preventing stale data from being presented as a daily result.
- Allows optional endpoints to fail independently: the core level refresh remains available and the partial-snapshot errors are recorded without storing secrets.
- Adds an automatic, non-destructive SQLite migration for the snapshot table and deletes snapshot history when a tracked character is removed.
- Includes `build.yaml` for current Home Assistant builds and a backup/rollback-aware `upgrade.sh`.

## 1.2.0

- Scheduled reports now include a real `@everyone` mention.
- `/schedule` now accepts a daily `time` in 24-hour `HH:MM` format and an IANA `timezone` instead of an hourly interval.
- The default scheduling timezone is `Australia/Sydney`; daylight-saving changes are handled automatically.
- `/characters`, `/levels` and scheduled reports sort characters by level from highest to lowest, with unknown levels last and alphabetical tie-breaking.
- `/schedule` checks the destination channel for View Channel, Send Messages, Embed Links and Mention Everyone permissions before saving.
- Preserves the existing open-to-everyone `/character-add` behaviour.
- Adds automatic migration from the earlier interval-based schedule table while retaining the persistent character database.

## 1.1.0

- Home Assistant local app packaging and persistent `/data` storage.
- Blizzard OAuth bearer-token correction.
