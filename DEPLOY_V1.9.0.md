# Safe v1.9.0 review and deployment

This update uses the existing repository and GHCR workflow. It does **not** require a Home Assistant host reboot, app reinstallation or data migration.

## 1. Review locally

1. Extract the review package.
2. Open `prototypes/COMPARISON.md` and review all five outputs.
3. In particular, review `prototypes/minimal_image_preview.png` at its normal size and `prototypes/table_preview.md` as plain monospaced text.
4. Confirm the desired Home Assistant defaults in `wow_forever_level_bot/config.yaml`.

The supplied image and payload prototypes are generated from `prototypes/current_leaderboard.json`. Reproduce them with:

```powershell
python .\prototypes\render_prototypes.py
```

## 2. Create a review branch on the new PC

Authenticate to GitHub on the new PC using GitHub Desktop or Git Credential Manager, then in PowerShell:

```powershell
git clone https://github.com/MashmanAU/wow-forever-home-assistant.git
cd .\wow-forever-home-assistant
git checkout -b release/v1.9.0
```

Copy the contents of the package's `repo` folder over the cloned working tree, including `.github` and `.gitignore`. Do not copy over or delete the cloned `.git` directory.

Review the change set:

```powershell
git status
git diff --stat
git diff --check
```

Commit and publish the review branch:

```powershell
git add .
git commit -m "Add minimal image and table leaderboards v1.9.0"
git push -u origin release/v1.9.0
```

Open a pull request into `main`. Require the **Test** workflow to pass before merging.

## 3. Build and publish

Merging to `main` runs **Build and publish app images** for `amd64` and `aarch64`. Confirm both jobs complete successfully and that the public GHCR packages contain tag `1.9.0` before updating Home Assistant.

Do not change the `image:` path in `config.yaml`; Home Assistant selects the architecture-specific image and the app version selects the `1.9.0` tag.

## 4. Protect the live installation

Before updating, keep the existing v1.8.0 app running and create an app-specific backup:

```bash
ha backups new --name "WoW Forever before v1.9.0" --app 27931aff_wow_forever_level_bot
```

Wait for completion and retain the returned backup slug.

## 5. Update without rebooting

1. In Home Assistant, open **Settings → Apps → App store** and refresh/reload the repository list if v1.9.0 is not yet shown.
2. Open **WoW Forever Level Bot** and select **Update**.
3. Do not uninstall the app and do not remove the repository.
4. Start the app if Home Assistant does not restart it automatically.
5. Check the log for normal Discord authentication and command synchronisation.

The SQLite database remains at `/data/wow_forever.db`; v1.9.0 makes no schema change.

## 6. Validate the selected production layout

In the Home Assistant Configuration page, select the render mode and fields. For the simplified graphical default use:

- `leaderboard_render_mode: minimal_image`
- `leaderboard_density: standard`
- `image_theme: dark_warcraft`
- class colours and class icons enabled
- level, 24-hour changes and lifetime deaths enabled
- rank, race, class text, level progress, professions, 7-day changes and notable activity disabled

Then select `table` and repeat `/daily-live-test` to compare the information-first alternative. The table needs **Embed Links** but not **Attach Files**.

Ensure the bot role has **Attach Files** in `#bot-stuff` and the scheduled channel. Then run:

```text
/daily-live-test
```

This command fetches current Blizzard data and reads existing baselines, but does not write snapshots, commentary history, schedules or next-run values. It calls the same delivery method as the scheduled report, suppresses all mentions and posts only to `#bot-stuff`.

## 7. Rollback trigger

Rollback if the app fails to start, Discord command sync fails, the selected render path and native fallback both fail, or the live test writes unexpected state. Stop the app and restore the pre-update app backup by its slug. Do not run both old and new app identities concurrently.
