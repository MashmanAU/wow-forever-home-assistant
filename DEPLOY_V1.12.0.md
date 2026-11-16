# Deploy v1.12.0

From the extracted release folder, run the existing one-command publisher:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\publish.ps1" -RepositoryPath "C:\Users\jagra\OneDrive\WowForeverBot\wow-forever-home-assistant"
```

The script validates the release, updates the clean `main` branch, runs the Python and publisher integration tests, copies the repository-ready files, commits and pushes.

The image-build workflow then retrieves the pinned class icons from `orourkek/Wow-Icons`, validates all nine PNGs and embeds them into each architecture-specific container. An unavailable or malformed icon fails the build rather than publishing an incomplete image.

After both GitHub workflows are green:

1. Refresh the Home Assistant app repository and install v1.12.0.
2. Restart the app and run `/daily-live-test`.
3. Confirm the post lands in the configured private channel with no mention.
4. Check several Warrior, Paladin, Hunter and caster rows to confirm the new class artwork, class-colour outline and optional rank overlay are clear.
5. Review the commentary. Significant level gains may now lead naturally; repeated topics should vary in wording and framing rather than being suppressed.
6. Confirm the existing production `/schedule` destination is unchanged.
