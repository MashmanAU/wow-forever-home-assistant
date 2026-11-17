# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.14.0

- Fixes daily level gains when consecutive scheduled snapshots are a few seconds or minutes either side of exactly 24 hours apart.
- Selects the snapshot nearest the intended 24-hour mark instead of falling back to a roughly 48-hour-old observation.
- Leaves a 24-hour change unknown when no suitably close daily baseline exists rather than showing a misleading value.
- Weights commentary across unlike scales: character levels cap at 60 and later gains count more, while profession tracks commonly span 150–300 points.
- Preserves v1.13.0 notification choices, presentation, class icons, data, schedules, Wowhead controls and safeguards.
- Makes no database schema change and creates no migration backup.

See `RELEASE_NOTES_V1.14.0.md`, `PUBLISHING.md` and `DEPLOY_V1.14.0.md`.
