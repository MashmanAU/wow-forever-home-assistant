[CmdletBinding()]
param(
    [switch]$ForceAssertionFailure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$publisher = Join-Path $repositoryRoot "publish.ps1"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("wow-publisher-test-" + [Guid]::NewGuid().ToString("N"))
$testFailure = $null

function Invoke-TestGit {
    param(
        [string]$WorkingDirectory,
        [string[]]$Arguments
    )

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
        throw "Test git command failed ($exitCode): git $($Arguments -join ' ')`n$($output -join "`n")"
    }
    return @($output | ForEach-Object { "$_" })
}

function Invoke-PublisherChild {
    param([string[]]$Arguments)

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
        $output = @(& pwsh -NoProfile -File $publisher @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        if ($hasNativeErrorPreference) {
            $PSNativeCommandUseErrorActionPreference = $previousNativeErrorPreference
        }
    }

    return [PSCustomObject]@{
        ExitCode = $exitCode
        Output = @($output | ForEach-Object { "$_" })
    }
}

try {
    if ($ForceAssertionFailure) {
        throw "Forced assertion failure for exit-code verification."
    }

    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    $remote = Join-Path $temporaryRoot "remote.git"
    $seed = Join-Path $temporaryRoot "seed"
    $clone = Join-Path $temporaryRoot "clone"
    $failureClone = Join-Path $temporaryRoot "failure-clone"
    $updater = Join-Path $temporaryRoot "updater"
    $release = Join-Path $temporaryRoot "release"

    New-Item -ItemType Directory -Path $remote, $seed, $release | Out-Null
    Invoke-TestGit -WorkingDirectory $remote -Arguments @("init", "--bare", "--initial-branch=main") | Out-Null
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("init", "-b", "main") | Out-Null
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("config", "user.name", "Publisher Integration Test") | Out-Null
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("config", "user.email", "publisher-test@example.invalid") | Out-Null
    Set-Content -LiteralPath (Join-Path $seed "README.md") -Value "baseline"
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("add", "README.md") | Out-Null
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("commit", "-m", "baseline") | Out-Null
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("remote", "add", "origin", $remote) | Out-Null
    Invoke-TestGit -WorkingDirectory $seed -Arguments @("push", "-u", "origin", "main") | Out-Null

    Invoke-TestGit -WorkingDirectory $temporaryRoot -Arguments @("clone", $remote, $clone) | Out-Null
    Invoke-TestGit -WorkingDirectory $temporaryRoot -Arguments @("clone", $remote, $failureClone) | Out-Null
    Invoke-TestGit -WorkingDirectory $temporaryRoot -Arguments @("clone", $remote, $updater) | Out-Null
    Invoke-TestGit -WorkingDirectory $clone -Arguments @("config", "user.name", "Publisher Integration Test") | Out-Null
    Invoke-TestGit -WorkingDirectory $clone -Arguments @("config", "user.email", "publisher-test@example.invalid") | Out-Null
    Invoke-TestGit -WorkingDirectory $failureClone -Arguments @("config", "user.name", "Publisher Integration Test") | Out-Null
    Invoke-TestGit -WorkingDirectory $failureClone -Arguments @("config", "user.email", "publisher-test@example.invalid") | Out-Null
    Invoke-TestGit -WorkingDirectory $updater -Arguments @("config", "user.name", "Publisher Integration Test") | Out-Null
    Invoke-TestGit -WorkingDirectory $updater -Arguments @("config", "user.email", "publisher-test@example.invalid") | Out-Null

    Set-Content -LiteralPath (Join-Path $updater "remote-update.txt") -Value "forces fetch informational stderr"
    Invoke-TestGit -WorkingDirectory $updater -Arguments @("add", "remote-update.txt") | Out-Null
    Invoke-TestGit -WorkingDirectory $updater -Arguments @("commit", "-m", "remote update") | Out-Null
    Invoke-TestGit -WorkingDirectory $updater -Arguments @("push", "origin", "main") | Out-Null

    $trackedFiles = @(Invoke-TestGit -WorkingDirectory $repositoryRoot -Arguments @("ls-files"))
    foreach ($relative in $trackedFiles) {
        if ([string]::IsNullOrWhiteSpace($relative)) {
            continue
        }
        $source = Join-Path $repositoryRoot $relative
        $destination = Join-Path $release $relative
        $destinationParent = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationParent)) {
            New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    $success = Invoke-PublisherChild -Arguments @($release, "-RepositoryPath", $clone, "-NoPush")
    if ($success.ExitCode -ne 0) {
        throw "Publisher rejected successful Git informational stderr:`n$($success.Output -join "`n")"
    }
    $successText = $success.Output -join "`n"
    if ($successText -notmatch '(?m)^From\s+') {
        throw "The success fixture did not produce the expected Git 'From ...' informational stderr line.`n$successText"
    }
    $subject = (Invoke-TestGit -WorkingDirectory $clone -Arguments @("log", "-1", "--pretty=%s")) -join ""
    if ($subject -ne "Release WoW Forever v1.10.0") {
        throw "Publisher did not create the expected release commit. Found: $subject"
    }

    $failure = Invoke-PublisherChild -Arguments @($release, "-RepositoryPath", $failureClone, "-Remote", "missing-remote", "-NoPush")
    if ($failure.ExitCode -eq 0) {
        throw "Publisher did not fail for a genuine Git remote error."
    }
    $failureText = $failure.Output -join "`n"
    if ($failureText -notmatch 'git fetch missing-remote main failed with exit code') {
        throw "Publisher did not surface the genuine Git failure and exit code.`n$failureText"
    }

    Write-Host "Git informational stderr with exit code 0: PASS"
    Write-Host "Genuine Git failure with non-zero exit code: PASS"
}
catch {
    $testFailure = $_
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($null -ne $testFailure) {
    Write-Error $testFailure -ErrorAction Continue
    exit 1
}

# The expected failing publisher child leaves $LASTEXITCODE set to 1. An
# explicit successful process exit prevents that deliberately tested value
# from leaking into the integration test's own GitHub Actions result.
exit 0
