[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$ReleasePath,

    [string]$RepositoryPath = (Get-Location).Path,

    [string]$Remote = "origin",

    [string]$Branch = "main",

    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Get-FullPath {
    param([string]$Path)
    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Path).Path)
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [switch]$Capture
    )

    if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        if (-not (Get-Variable -Name RepoRoot -Scope Script -ErrorAction SilentlyContinue)) {
            throw "Invoke-Git requires WorkingDirectory before the repository root has been resolved."
        }
        $WorkingDirectory = $script:RepoRoot
    }

    # Windows PowerShell converts native stderr records into PowerShell error
    # records. Git legitimately writes progress and informational lines such as
    # "From https://github.com/..." to stderr even when it exits successfully.
    # Temporarily keep native stderr non-terminating, capture both streams, and
    # decide success exclusively from Git's process exit code.
    $previousErrorActionPreference = $ErrorActionPreference
    $hasNativeErrorPreference = $null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue)
    if ($hasNativeErrorPreference) {
        $previousNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
    }

    try {
        $ErrorActionPreference = "Continue"
        if ($hasNativeErrorPreference) {
            $PSNativeCommandUseErrorActionPreference = $false
        }
        $output = @(& git -C $WorkingDirectory @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        if ($hasNativeErrorPreference) {
            $PSNativeCommandUseErrorActionPreference = $previousNativeErrorPreference
        }
    }

    if ($exitCode -ne 0) {
        $detail = ($output | ForEach-Object { "$_" }) -join [Environment]::NewLine
        throw "git $($Arguments -join ' ') failed with exit code $exitCode.`n$detail"
    }

    if ($Capture) {
        return @($output | ForEach-Object { "$_" })
    }

    $output | ForEach-Object { Write-Host "$_" }
}

function Test-ZipEntrySafety {
    param([string]$ZipPath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName.Replace("\", "/")
            $segments = @($name.Split([char[]]@('/'), [System.StringSplitOptions]::RemoveEmptyEntries))
            if (
                [string]::IsNullOrWhiteSpace($name) -or
                $name.StartsWith("/") -or
                $name -match "^[A-Za-z]:" -or
                $segments -contains ".."
            ) {
                throw "The release ZIP contains an unsafe path: $($entry.FullName)"
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}

function Find-ReleaseRepository {
    param([string]$SearchRoot)

    $candidates = New-Object System.Collections.Generic.List[string]

    function Add-Candidate {
        param([string]$Candidate)
        if (
            (Test-Path -LiteralPath (Join-Path $Candidate "repository.yaml") -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $Candidate "wow_forever_level_bot/config.yaml") -PathType Leaf)
        ) {
            $resolved = [System.IO.Path]::GetFullPath($Candidate)
            if (-not $candidates.Contains($resolved)) {
                $candidates.Add($resolved)
            }
        }
    }

    Add-Candidate -Candidate $SearchRoot
    Add-Candidate -Candidate (Join-Path $SearchRoot "repo")

    Get-ChildItem -LiteralPath $SearchRoot -Directory -Force | ForEach-Object {
        Add-Candidate -Candidate $_.FullName
        Add-Candidate -Candidate (Join-Path $_.FullName "repo")
    }

    if ($candidates.Count -ne 1) {
        $found = if ($candidates.Count -eq 0) { "none" } else { $candidates -join ", " }
        throw "Expected exactly one repository-ready release folder; found $found."
    }

    return $candidates[0]
}

function Find-ReleaseRoot {
    param(
        [string]$SearchRoot,
        [string]$SourceRepository
    )

    $parent = Split-Path -Parent $SourceRepository
    if ((Split-Path -Leaf $SourceRepository) -eq "repo") {
        return $parent
    }
    return $SearchRoot
}

function Test-ReleaseManifest {
    param([string]$ReleaseRoot)

    $manifestPath = Join-Path $ReleaseRoot "MANIFEST.sha256"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        Write-Host "No MANIFEST.sha256 found; continuing with structural and version checks." -ForegroundColor Yellow
        return
    }

    Write-Step "Verifying package checksums"
    $checked = 0
    foreach ($line in Get-Content -LiteralPath $manifestPath) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        if ($line -notmatch "^([0-9a-fA-F]{64})\s+\./(.+)$") {
            throw "Invalid MANIFEST.sha256 line: $line"
        }

        $expected = $Matches[1].ToLowerInvariant()
        $relative = $Matches[2].Replace("/", [System.IO.Path]::DirectorySeparatorChar)
        if (
            [System.IO.Path]::IsPathRooted($relative) -or
            $relative.Contains(":") -or
            (($relative.Split([char[]]@([System.IO.Path]::DirectorySeparatorChar), [System.StringSplitOptions]::RemoveEmptyEntries)) -contains "..")
        ) {
            throw "Unsafe path in MANIFEST.sha256: $relative"
        }

        $filePath = Join-Path $ReleaseRoot $relative
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            throw "Manifest file is missing: $relative"
        }

        $actual = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
            throw "Checksum mismatch for $relative"
        }
        $checked++
    }

    if ($checked -eq 0) {
        throw "MANIFEST.sha256 did not contain any file entries."
    }
    Write-Host "Verified $checked package files."
}

function Test-ForbiddenFiles {
    param([string]$SourceRepository)

    $forbiddenDirectoryNames = @(
        ".git", ".venv", "__pycache__", ".pytest_cache", "data", "backups"
    )
    $forbiddenFilePatterns = @(
        ".env", ".env.*", "secrets.yaml", "secrets.yml", "credentials.json",
        "service-account*.json", "*.pem", "*.key", "*.pfx", "*.p12",
        "id_rsa", "id_ed25519", "*.db", "*.db-*", "*.sqlite", "*.sqlite3",
        "options.json", "*.token", "*.secret"
    )

    $blocked = New-Object System.Collections.Generic.List[string]
    Get-ChildItem -LiteralPath $SourceRepository -Recurse -Force | ForEach-Object {
        $relative = $_.FullName.Substring($SourceRepository.Length).TrimStart("\", "/")
        if ($_.PSIsContainer) {
            if ($forbiddenDirectoryNames -contains $_.Name.ToLowerInvariant()) {
                $blocked.Add($relative)
            }
            return
        }

        foreach ($pattern in $forbiddenFilePatterns) {
            if ($_.Name -like $pattern) {
                $blocked.Add($relative)
                break
            }
        }
    }

    if ($blocked.Count -gt 0) {
        throw "The release contains blocked credential, database or build-state paths:`n - $($blocked -join "`n - ")"
    }
}

function Test-EmbeddedSecrets {
    param([string]$SourceRepository)

    $configPath = Join-Path $SourceRepository "wow_forever_level_bot/config.yaml"
    $configText = Get-Content -LiteralPath $configPath -Raw
    $secretKeys = @("discord_token", "blizzard_client_secret", "openai_api_key")
    $populated = New-Object System.Collections.Generic.List[string]

    foreach ($key in $secretKeys) {
        $pattern = "(?m)^\s*" + [regex]::Escape($key) + "\s*:\s*(.*?)\s*$"
        if ($configText -match $pattern) {
            $value = $Matches[1].Split("#")[0].Trim().Trim('"').Trim("'")
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $populated.Add($key)
            }
        }
    }

    if ($populated.Count -gt 0) {
        throw "The release contains populated secret settings in config.yaml: $($populated -join ', ')"
    }
}

function Get-ReleaseVersion {
    param([string]$SourceRepository)

    $initPath = Join-Path $SourceRepository "wow_forever_level_bot/wow_forever_bot/__init__.py"
    $configPath = Join-Path $SourceRepository "wow_forever_level_bot/config.yaml"
    $projectPath = Join-Path $SourceRepository "wow_forever_level_bot/pyproject.toml"

    $initText = Get-Content -LiteralPath $initPath -Raw
    $configText = Get-Content -LiteralPath $configPath -Raw
    $projectText = Get-Content -LiteralPath $projectPath -Raw

    if ($initText -notmatch '(?m)^__version__\s*=\s*["'']([^"'']+)["'']') {
        throw "Could not read __version__ from $initPath"
    }
    $versions = New-Object System.Collections.Generic.List[string]
    $versions.Add($Matches[1])

    if ($configText -notmatch '(?m)^version:\s*["'']?([^"''\s]+)["'']?\s*$') {
        throw "Could not read the Home Assistant version from $configPath"
    }
    $versions.Add($Matches[1])

    if ($projectText -notmatch '(?m)^version\s*=\s*["'']([^"'']+)["'']\s*$') {
        throw "Could not read the project version from $projectPath"
    }
    $versions.Add($Matches[1])

    $unique = @($versions | Sort-Object -Unique)
    if ($unique.Count -ne 1) {
        throw "Release version mismatch: $($versions -join ', ')"
    }
    if ($unique[0] -notmatch '^\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?$') {
        throw "Release version has an unexpected format: $($unique[0])"
    }

    return $unique[0]
}

function Copy-ReleaseRepository {
    param(
        [string]$SourceRepository,
        [string]$DestinationRepository
    )

    Write-Step "Removing tracked files that are absent from the release"
    $trackedFiles = @(Invoke-Git -Arguments @("ls-files") -Capture)
    foreach ($relative in $trackedFiles) {
        if ([string]::IsNullOrWhiteSpace($relative)) {
            continue
        }
        $sourcePath = Join-Path $SourceRepository $relative
        $destinationPath = Join-Path $DestinationRepository $relative
        if (
            -not (Test-Path -LiteralPath $sourcePath) -and
            (Test-Path -LiteralPath $destinationPath -PathType Leaf)
        ) {
            Remove-Item -LiteralPath $destinationPath -Force
        }
    }

    Write-Step "Copying repository-ready release files"
    Get-ChildItem -LiteralPath $SourceRepository -File -Recurse -Force | ForEach-Object {
        $relative = $_.FullName.Substring($SourceRepository.Length).TrimStart("\", "/")
        if ($relative -eq ".git" -or $relative.StartsWith(".git\") -or $relative.StartsWith(".git/")) {
            return
        }

        $destination = Join-Path $DestinationRepository $relative
        $destinationParent = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationParent -PathType Container)) {
            New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        }
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
    }
}

$temporaryDirectory = $null
$copyStarted = $false
$initialHead = $null
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is not installed or is not available on PATH."
    }

    $requestedRepository = Get-FullPath -Path $RepositoryPath
    try {
        $repoProbe = @(Invoke-Git -WorkingDirectory $requestedRepository -Arguments @("rev-parse", "--show-toplevel") -Capture)
    }
    catch {
        throw "RepositoryPath is not inside a Git working tree: $requestedRepository`n$($_.Exception.Message)"
    }
    $script:RepoRoot = [System.IO.Path]::GetFullPath("$($repoProbe[-1])")

    Write-Step "Checking repository"
    $currentBranch = ((Invoke-Git -Arguments @("branch", "--show-current") -Capture) -join "").Trim()
    if ($currentBranch -ne $Branch) {
        throw "The repository must be on branch '$Branch'; current branch is '$currentBranch'."
    }

    $statusBefore = @(Invoke-Git -Arguments @("status", "--porcelain", "--untracked-files=all") -Capture)
    if ($statusBefore.Count -gt 0 -and ($statusBefore -join "").Trim().Length -gt 0) {
        throw "The repository has uncommitted or untracked files. Commit, move or remove them before publishing.`n$($statusBefore -join "`n")"
    }

    Write-Step "Updating $Remote/$Branch"
    Invoke-Git -Arguments @("fetch", $Remote, $Branch)
    Invoke-Git -Arguments @("pull", "--ff-only", $Remote, $Branch)
    $initialHead = ((Invoke-Git -Arguments @("rev-parse", "HEAD") -Capture) -join "").Trim()

    if ([string]::IsNullOrWhiteSpace($ReleasePath)) {
        if (Test-Path -LiteralPath (Join-Path $PSScriptRoot "repo") -PathType Container) {
            $searchRoot = Get-FullPath -Path $PSScriptRoot
        }
        else {
            throw "Provide the release ZIP or extracted package path, for example: .\publish.ps1 'C:\Downloads\WoW-Forever-Home-Assistant-v1.10.0-review.zip'"
        }
    }
    else {
        $resolvedReleasePath = Get-FullPath -Path $ReleasePath
        if (Test-Path -LiteralPath $resolvedReleasePath -PathType Leaf) {
            if ([System.IO.Path]::GetExtension($resolvedReleasePath) -ne ".zip") {
                throw "ReleasePath must be a ZIP file or extracted package directory."
            }
            Test-ZipEntrySafety -ZipPath $resolvedReleasePath
            $temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("wow-forever-publish-" + [Guid]::NewGuid().ToString("N"))
            New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null
            Write-Step "Extracting release package"
            Expand-Archive -LiteralPath $resolvedReleasePath -DestinationPath $temporaryDirectory -Force
            $searchRoot = $temporaryDirectory
        }
        elseif (Test-Path -LiteralPath $resolvedReleasePath -PathType Container) {
            $searchRoot = $resolvedReleasePath
        }
        else {
            throw "ReleasePath does not exist: $resolvedReleasePath"
        }
    }

    $sourceRepository = Find-ReleaseRepository -SearchRoot $searchRoot
    $releaseRoot = Find-ReleaseRoot -SearchRoot $searchRoot -SourceRepository $sourceRepository
    Test-ReleaseManifest -ReleaseRoot $releaseRoot
    Test-ForbiddenFiles -SourceRepository $sourceRepository
    Test-EmbeddedSecrets -SourceRepository $sourceRepository
    $version = Get-ReleaseVersion -SourceRepository $sourceRepository
    Write-Host "Release version: $version" -ForegroundColor Green

    $copyStarted = $true
    Copy-ReleaseRepository -SourceRepository $sourceRepository -DestinationRepository $script:RepoRoot

    Write-Step "Validating copied files"
    $copiedVersion = Get-ReleaseVersion -SourceRepository $script:RepoRoot
    if ($copiedVersion -ne $version) {
        throw "Copied release version mismatch: expected $version, found $copiedVersion"
    }
    Invoke-Git -Arguments @("diff", "--check")

    $changes = @(Invoke-Git -Arguments @("status", "--short") -Capture)
    if ($changes.Count -eq 0 -or ($changes -join "").Trim().Length -eq 0) {
        Write-Host "The repository already contains WoW Forever v$version. Nothing to publish." -ForegroundColor Yellow
        exit 0
    }

    Write-Step "Changes to publish"
    $changes | ForEach-Object { Write-Host "$_" }
    Invoke-Git -Arguments @("diff", "--stat")

    Write-Step "Staging release"
    Invoke-Git -Arguments @("add", "-A")
    Invoke-Git -Arguments @("diff", "--cached", "--check")
    Invoke-Git -Arguments @("diff", "--cached", "--stat")

    $stagedFiles = @(Invoke-Git -Arguments @("diff", "--cached", "--name-only") -Capture)
    $noStagedChanges = $stagedFiles.Count -eq 0 -or ($stagedFiles -join "").Trim().Length -eq 0

    if ($noStagedChanges) {
        Write-Host "No staged changes remain. Nothing to publish." -ForegroundColor Yellow
        exit 0
    }

    $message = "Release WoW Forever v$version"
    Write-Step "Committing '$message'"
    Invoke-Git -Arguments @("commit", "-m", $message)

    if ($NoPush) {
        Write-Host "NoPush was selected. Commit created locally; nothing was pushed." -ForegroundColor Yellow
    }
    else {
        Write-Step "Pushing $Branch to $Remote"
        Invoke-Git -Arguments @("push", $Remote, $Branch)
        Write-Host "WoW Forever v$version was pushed. Wait for GitHub Actions to turn green, then update the app in Home Assistant." -ForegroundColor Green
    }
}
catch {
    Write-Host "`nPublish failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($copyStarted -and $script:RepoRoot) {
        Write-Host "The working tree may contain release changes. Review them with 'git status'." -ForegroundColor Yellow
        if ($initialHead) {
            Write-Host "Because publishing started from a clean tree, 'git reset --hard $initialHead' restores the pre-publish commit if required." -ForegroundColor Yellow
        }
    }
    exit 1
}
finally {
    if ($temporaryDirectory -and (Test-Path -LiteralPath $temporaryDirectory)) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}
