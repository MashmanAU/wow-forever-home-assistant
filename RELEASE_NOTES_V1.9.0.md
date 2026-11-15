# WoW Forever Level Bot v1.9.0

## Outcome

v1.9.0 adds two deliberately simpler presentation modes after real Discord testing showed that the detailed two-column PNG was too small inline. The existing `native_embed`, `components_v2` and `image` modes remain available and unchanged in purpose.

## New modes

- **`minimal_image`** — a narrow 760 px, single-column PNG inspired by the supplied reference. Each row prioritises a large deterministic class glyph, level badge, immediately adjacent 24-hour level movement, large class-coloured name and optional lifetime deaths at the far right.
- **`table`** — a Discord-native monospaced table written directly in Python. Its core order is Character, Level, 24h, optional 7d, Deaths, then optional secondary details. It uses `-` for no change, Unicode display-width calculations and bounded layouts for mobile.

## Simplified defaults

New installations default to `minimal_image` with rank, race text, class text, level progress, professions and notable activity disabled. Level, 24-hour movement, lifetime deaths, class glyphs and class colours remain enabled. Every existing field is still configurable in Home Assistant.

Existing Home Assistant installations normally retain their saved field values during update. To reproduce the supplied minimal preview, set:

```yaml
leaderboard_render_mode: minimal_image
show_rank: false
show_race: false
show_class: false
show_level: true
show_level_progress: false
show_lifetime_deaths: true
show_professions: false
show_24h_changes: true
show_7d_changes: false
show_notable_activity: false
use_class_colours: true
show_class_icons: true
```

## Preserved behaviour

- Existing Native Embed, Components V2 and detailed Image modes.
- Home Assistant display toggles and image controls.
- Live Blizzard data, controlled snapshot history and schedule advancement.
- OpenAI commentary and filtered Wowhead RSS.
- Production `@everyone` and mention-free `/daily-live-test`.
- Identical scheduled/live-test delivery path.
- GitHub Actions tests and multi-architecture GHCR publishing.
- Native embed fallback if either image renderer fails.

No database schema change is required.
