# WoW Forever Level Bot v1.8.0

## Outcome

v1.8.0 corrects the missing display customisation and adds three production-capable leaderboard renderers. The default is a deterministic two-column PNG generated locally with Pillow. A native Discord embed remains both a selectable text mode and the automatic fallback.

## Display modes

- **image** — class-coloured names, class badges, graphical level bars and one/two-column themes.
- **components_v2** — Discord-native container, text displays and separators; commentary is sent immediately before it as a normal Discord message.
- **native_embed** — searchable/copyable text presentation with Unicode progress bars.

## Home Assistant controls

Users can choose render mode, density, image columns/theme and whether rank, race, class, level, progress, deaths, professions, 24-hour changes, seven-day changes and notable activity are shown. Class colours, class badges and profession markers are independently controllable.

## Safety and compatibility

- No database migration.
- No change to Blizzard collection or snapshot history.
- No change to OpenAI commentary grounding or Wowhead filtering.
- No AI image generation is used for live data.
- `/daily-live-test` remains read-only and now calls the exact production delivery method.
- Scheduled `@everyone` remains restricted to the scheduled commentary message.
- Image and Components V2 failures are logged and fall back to the native embed.
- GitHub Actions tests both source and release invariants; GHCR publishes versioned `amd64` and `aarch64` images.
