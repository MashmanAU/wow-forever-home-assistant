# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.13.0

- Adds `daily_notification` with `everyone`, `here` and `none` choices in Home Assistant.
- Defaults to `everyone` to preserve the existing scheduled behaviour.
- Applies the setting only to scheduled production reports; both test commands remain mention-free.
- Allows no-notification schedules without requiring the Discord Mention Everyone permission.
- Applies changes after Save + Restart without replacing the stored schedule.
- Preserves v1.12.0 presentation, class icons, announcer logic, data, schedules, Wowhead controls and safeguards.
- Makes no database schema change and creates no migration backup.

See `RELEASE_NOTES_V1.13.0.md`, `PUBLISHING.md` and `DEPLOY_V1.13.0.md`.
