# Deploy v1.14.0

From the extracted release folder, run the existing one-command publisher:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\publish.ps1" -RepositoryPath "C:\Users\jagra\OneDrive\WowForeverBot\wow-forever-home-assistant"
```

The script validates the release, updates the clean `main` branch, runs the Python and publisher integration tests, copies the repository-ready files, commits and pushes.

After both GitHub workflows are green:

1. Refresh the Home Assistant app repository and install v1.14.0.
2. Save and restart the app. No database migration or schedule replacement is required.
3. Run `/daily-live-test` in the configured private test channel.
4. Confirm the green figure for a character is the difference from the stored snapshot nearest 24 hours earlier. A character without a suitable 18–30 hour baseline should show `-`.
5. Confirm a day containing one or two meaningful character levels is no longer routinely led by a larger raw count of low-level profession points.
6. Allow the next scheduled production report to run and confirm the configured `@everyone`, `@here` or no-notification behaviour remains unchanged.

The two supplied comparison screenshots were both timestamped 16 November 2026 (3:37 pm and 4:30 pm), so they are not themselves two daily baselines. The regression test reproduces the actual scheduling edge case directly: yesterday's snapshot at 23h55 is selected instead of a two-day-old snapshot.
