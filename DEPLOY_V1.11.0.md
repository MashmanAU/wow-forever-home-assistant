# Deploy v1.11.0

From the extracted release folder, run the existing one-command publisher:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\publish.ps1" -RepositoryPath "C:\Users\jagra\OneDrive\WowForeverBot\wow-forever-home-assistant"
```

The script validates the release, updates the clean `main` branch, runs the Python and publisher integration tests, copies the repository-ready files, commits and pushes.

After both GitHub workflows are green:

1. Refresh the Home Assistant app repository and install v1.11.0.
2. Confirm `leaderboard_render_mode` is `split_image` and `split_image_rows` is `6` (or choose 2–12).
3. Confirm `test_channel_name` matches exactly one Discord text channel.
4. Restart the app and run `/daily-live-test`.
5. Confirm the post lands in the configured private channel with no mention, while the existing production `/schedule` destination is unchanged.
