# One-command release publishing

`publish.ps1` turns a repository-ready WoW Forever review ZIP into one Git commit and pushes it to `main`.

## Normal workflow

Open PowerShell in the cloned `wow-forever-home-assistant` repository and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\publish.ps1" -RepositoryPath "C:\Users\jagra\OneDrive\WowForeverBot\wow-forever-home-assistant"
```

The script will:

1. confirm that the clone is clean and on `main`;
2. fetch and fast-forward from `origin/main`;
3. reject unsafe ZIP paths and blocked credential, database and build-state files;
4. verify `MANIFEST.sha256` when it is present;
5. confirm that the Python, Home Assistant and package versions match;
6. copy the release's `repo` contents into the clone and remove obsolete tracked files;
7. show and validate the Git change set;
8. stage and commit it as `Release WoW Forever v<version>`; and
9. push `main` to GitHub.

Git commonly writes ordinary progress and informational messages to stderr. Lines such as `From https://github.com/...` remain visible and do not stop publishing when Git returns exit code `0`. A non-zero Git exit code still stops the script and includes Git's output in the failure message.

After the push, wait for both GitHub Actions workflows to turn green, then use **Home Assistant → Check for updates → Update**.

## Running from an extracted review package

The review package carries a copy of `publish.ps1` beside its `repo` folder. Extract the package, open PowerShell in the extracted package folder and run:

```powershell
.\publish.ps1 -RepositoryPath "C:\path\to\wow-forever-home-assistant"
```

With no `ReleasePath` argument, the script automatically publishes the sibling `repo` folder and updates the publisher in the clone. Future releases can use the publisher already in the repository.

If Windows blocks local scripts, use the process-only bypass without changing the machine policy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publish.ps1 -RepositoryPath "C:\path\to\wow-forever-home-assistant"
```

## Safety conditions

The script deliberately stops rather than guessing when:

- the clone is not on `main`;
- the working tree contains modified or untracked files;
- `origin/main` cannot be fast-forwarded;
- the ZIP contains an absolute or parent-traversal path;
- package checksums fail;
- repository structure or versions are inconsistent; or
- blocked credential, private-key, database, runtime-data or build-cache files are present.

The release ZIP should be kept outside the Git clone so the clean-tree check is not tripped.

## Local validation without pushing

To create the release commit locally but not push it:

```powershell
.\publish.ps1 "C:\Users\you\Downloads\WoW-Forever-Home-Assistant-v1.10.0-review.zip" -NoPush
```

Review it with:

```powershell
git show --stat --oneline HEAD
```

Push later with `git push origin main`, or undo the local test commit with `git reset --hard HEAD~1` if it has not been pushed.
