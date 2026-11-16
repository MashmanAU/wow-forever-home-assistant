# WoW Forever Level Bot v1.13.0

## Outcome

v1.13.0 makes the scheduled Discord notification configurable as `@everyone`, `@here` or no mention, while leaving test posts unconditionally mention-free.

## Daily notification setting

- Adds `daily_notification` to the Home Assistant app configuration.
- Provides three validated choices:
  - `everyone` — sends `@everyone`;
  - `here` — sends `@here`; and
  - `none` — sends no mention.
- Defaults to `everyone` so an upgrade does not silently change an existing production schedule's behaviour.
- Reads the configured value whenever the app starts. Save + Restart is sufficient; `/schedule` does not need to be rerun merely to change the notification.
- Uses Discord's explicit allowed-mentions policy for `everyone` and `here`, with user mentions, role mentions and replied-user mentions disabled.
- Uses `AllowedMentions.none()` when `none` is selected.

## Scheduling and safeguards

- `/schedule` requires **Mention @everyone, @here and All Roles** only when `everyone` or `here` is configured.
- A `none` schedule still validates View Channel, Send Messages and Embed Links, but is not blocked by the mention permission.
- The schedule confirmation states the active notification behaviour.
- The existing schedule database remains unchanged: notification mode is Home Assistant app configuration rather than per-guild schedule data.
- `/daily-post-test` and `/daily-live-test` continue to pass `AllowedMentions.none()` and never use the configured production notification.

## Preserved without migration

- Split Image and Table remain the two selectable presentation modes, with the native text fallback unchanged.
- The pinned class icons and v1.12.0 announcer editorial logic remain in place.
- Tracked characters, snapshot history, commentary memory, schedule time and destination, Wowhead controls, read-only live-test boundaries, GitHub Actions/GHCR delivery and the corrected `publish.ps1` are preserved.

There is no database schema change and no backup step is required for this release.
