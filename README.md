# WoW Forever Home Assistant

Repository-backed Home Assistant app for the WoW Forever Discord level bot.

## v1.10.0

- Adds `split_image`, a Components V2 delivery mode that renders the proven Minimal Image design as five-row PNG chunks.
- Sends an 18-character roster as four vertically stacked media blocks containing 5, 5, 5 and 3 rows.
- Uses one Media Gallery per attachment rather than a multi-image gallery grid, preserving the 540 px image width and existing typography.
- Keeps commentary in a Components V2 Text Display and preserves scheduled `@everyone` controls.
- Uses the same production sender for scheduled reports and the read-only `/daily-live-test`.
- Falls back to the native text embed if rendering, attachment creation or Components V2 delivery fails.
- Retains `minimal_image` as the default until the split layout has been assessed in the real Discord client.
- Preserves the corrected one-command `publish.ps1` workflow, including manifest, version, secret-file and Git exit-code validation.
- Makes no database schema change.

See `prototypes/split_image_components_v2_preview.png`, `PUBLISHING.md` and `DEPLOY_V1.10.0.md`.
