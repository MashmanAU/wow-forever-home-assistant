# Deploy v1.13.0

From the extracted release folder, run the existing one-command publisher:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\publish.ps1" -RepositoryPath "C:\Users\jagra\OneDrive\WowForeverBot\wow-forever-home-assistant"
```

The script validates the release, updates the clean `main` branch, runs the Python and publisher integration tests, copies the repository-ready files, commits and pushes.

After both GitHub workflows are green:

1. Refresh the Home Assistant app repository and install v1.13.0.
2. In the app configuration, set **Daily notification** to `everyone`, `here` or `none`.
3. Save and restart the app. Do not rerun `/schedule` unless the report time or destination also needs to change.
4. Run `/daily-live-test` and confirm it posts in the configured private test channel without any mention, regardless of the selected production notification.
5. Allow the next scheduled production report to run, or use a temporary schedule, and confirm the selected behaviour:
   - `everyone` renders and notifies `@everyone`;
   - `here` renders and notifies `@here`; or
   - `none` contains no mention.
6. For `everyone` or `here`, confirm the bot role has **Mention @everyone, @here and All Roles** in the production channel. This permission is not required for `none`.
7. Confirm the existing production schedule time and destination are unchanged.
