# Publish and test v1.10.0

## Review gate

Before publishing:

1. Open `prototypes/split_image_components_v2_preview.png`.
2. Read `RELEASE_NOTES_V1.10.0.md`.
3. Confirm the repository clone is clean and on `main`.
4. Keep the release ZIP outside the Git clone.

## One-command publish

Extract the release package. Open PowerShell in the extracted `WoW-Forever-Home-Assistant-v1.10.0-review` folder and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\publish.ps1" -RepositoryPath "C:\Users\jagra\OneDrive\WowForeverBot\wow-forever-home-assistant"
```

No manual copy, `git add`, commit or push is required. The publisher:

- confirms the clone is clean and on `main`;
- fetches and fast-forwards `origin/main`;
- validates ZIP paths when a ZIP is supplied;
- verifies `MANIFEST.sha256`;
- rejects credentials, databases, private keys and build-state files;
- confirms all release versions match;
- copies the repository-ready files and removes obsolete tracked files;
- runs `git diff --check`;
- stages and commits `Release WoW Forever v1.10.0`; and
- pushes `main` to GitHub.

Normal Git informational stderr does not cause a false failure; a non-zero Git exit code still stops the publisher.

## GitHub and Home Assistant gate

1. Wait for **Test** and **Build and publish app images** to pass.
2. Confirm both `amd64` and `aarch64` packages are built for `1.10.0`.
3. In Home Assistant, check for app updates and install v1.10.0.
4. Set `leaderboard_render_mode` to `split_image`.
5. Restart the app.
6. Run `/daily-live-test` in `#bot-stuff`.

The acceptance criterion is that the five-row blocks are materially larger and easier to read inline than the previous single 18-row attachment. If not, select `table` or return to `minimal_image`; no data rollback is required.

## Rollback

Select a previous render mode for an immediate presentation-only rollback. For an application rollback, revert the v1.10.0 Git commit and let the GHCR workflow rebuild. The database schema is unchanged.
