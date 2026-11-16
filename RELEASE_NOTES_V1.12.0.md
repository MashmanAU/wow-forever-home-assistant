# WoW Forever Level Bot v1.12.0

## Outcome

v1.12.0 replaces the placeholder class glyphs with the selected Unlicensed PNG set and resets the announcer so it reports the most significant verified story instead of steering away from levelling.

## Class icons

- Uses the nine 64×64 PNGs from `orourkek/Wow-Icons`: Druid, Hunter, Mage, Paladin, Priest, Rogue, Shaman, Warlock and Warrior.
- Pins the artwork to asset commit `5d9ad053876920138f68d69a4197fc18771b9505` rather than following a moving branch.
- Downloads and validates the assets only during the GitHub container build; the running app performs no artwork network requests.
- Rejects malformed files or dimensions other than 64×64 so a changed/error response cannot silently become a production icon.
- Fits each image into the existing 48 px rounded badge, retains the class-colour outline and rank overlay, and uses the prior generated glyph if a local file is missing or invalid.
- Includes the upstream source notice and Unlicense text.

## Announcer editorial reset

- Removes the fixed instruction to prefer achievements, professions, gear, PvP, rankings, XP or news over another levels-and-deaths story.
- Reviews every supplied activity category on equal terms and chooses by significance, novelty within today's facts and entertainment value.
- Explicitly permits levelling to lead whenever it is the clearest story, including on consecutive days.
- Treats the deterministic `primary_story_angle` as a fallback hint rather than a reason to ignore stronger supplied facts.
- Applies anti-repetition to openings, language, framing, jokes and sentence rhythm, not to the factual topic itself.
- Keeps fact integrity, supplied-news-only rules, structured output, word limits, similarity checking, one rewrite and deterministic fallback code-owned.
- Retains editable Announcer Style and Custom Style Notes.

## Preserved without migration

- Split Image and Table remain the two selectable presentation modes.
- `split_image_rows` remains 2–12 with a default of 6.
- Both test commands continue to use the configured private test channel with mentions suppressed.
- Production scheduling, tracked characters, SQLite history, Wowhead filtering, read-only live-test boundaries, GitHub Actions/GHCR delivery and the corrected `publish.ps1` remain in place.

There is no database schema change and no backup step is required for this release.
