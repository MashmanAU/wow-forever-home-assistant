# WoW Forever Level Bot v1.14.0

## Outcome

v1.14.0 corrects the green 24-hour level gains and makes commentary compare character levels and profession skill on their proper scales.

## Correct daily gains

- The prior algorithm accepted only snapshots at least exactly 24 hours old.
- A normal scheduled run a few seconds or minutes early could therefore reject yesterday's snapshot and compare the current level with the snapshot from roughly two days ago.
- The new algorithm selects the stored snapshot nearest the intended 24-hour mark within an 18–30 hour tolerance.
- This symmetric window also covers ordinary scheduler drift and 23/25-hour daylight-saving intervals.
- If no snapshot is close enough, the change remains unknown and the image shows `-` rather than presenting a stale interval as a daily gain.
- Seven-day deltas now use the same nearest-target principle within ±12 hours.
- Rank movement continues to require a valid daily baseline for every currently ranked character.

## Scale-aware commentary

- Profession gains now carry current skill and maximum-skill context in the controlled commentary payload.
- Profession significance is normalised against its maximum and completion range rather than using raw points.
- Character-level significance applies a substantial base score to every gained level and increases towards level 60.
- As a result, one or two gains at higher character levels outrank a large burst of low-level crafting skill while genuinely notable profession progress remains eligible.
- The OpenAI editorial prompt explicitly states that character levels cap at 60, profession tracks commonly span 150–300 points, and the raw values must not be equated.
- The deterministic fallback uses the same scale-aware selection rules.

## Verification and compatibility

- Regression tests cover a previous snapshot 23 hours 55 minutes old, stale-baseline rejection, profession scale metadata and level-versus-profession selection.
- Existing v1.13.0 `@everyone`, `@here` and no-notification choices are unchanged.
- Split Image, Table, native fallback, test-command isolation, tracked characters, schedules, snapshot history, commentary memory and Wowhead controls are preserved.
- There is no database schema change and no backup step is required.
