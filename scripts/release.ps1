param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = [System.IO.Path]::GetFullPath(([System.IO.Path]::Combine($PSScriptRoot, '..', '..')))
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location $repoRoot

Write-Host "==> Releaser starting for $Version"

$originalTag = $Version
if ($Version -notmatch '^v') {
    $Version = "v$Version"
}

if (git tag --list $Version) {
    throw "Tag $Version already exists locally"
}

$versionFile = [System.IO.Path]::Combine($repoRoot, 'src', 'snipcontext', '__init__.py')
$versionFile = [System.IO.Path]::GetFullPath($versionFile)
if (-not (Test-Path $versionFile)) {
    throw "Version file not found: $versionFile"
}

$content = Get-Content $versionFile
if ($content -match "__version__\s*=\s*""(.+?)""") {
    $oldVersion = $Matches[1]
} else {
    $oldVersion = 'unknown'
}
if ($oldVersion -eq $originalTag) {
    throw "Version file is already set to $originalTag"
}

Write-Host "==> Bumping version from $oldVersion to $originalTag"
$newContent = $content -replace "(__version__\s*=\s*"")[^""]+("")", "`${1}$originalTag`$2"
if ($newContent -eq $content) {
    throw "Failed to update __version__ in $versionFile"
}
Set-Content -Path $versionFile -Value $newContent -NoNewline

$diff = git diff -- $versionFile
Write-Host "==> Version diff:`n$diff"

$env:PYTHONPATH = "$repoRoot\src"
$allPassed = $false
$testPassed = $false
$qualityPassed = $false
$noUncommittedChanges = $false

try {
    Write-Host "==> Running quality checks"
    $quality = & python -m ruff check src/snipcontext tests
    if ($LASTEXITCODE -ne 0) { throw "Ruff check failed:`n$quality" }
    $qualityPassed = $true

    Write-Host "==> Running format check"
    $fmt = & python -m ruff format --check src/snipcontext tests
    if ($LASTEXITCODE -ne 0) { throw "Ruff format check failed:`n$fmt" }

    Write-Host "==> Running tests"
    $tests = & python -m pytest tests/ -x -q --ignore=tests/test_search.py
    Write-Host $tests
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
    $testPassed = $true

    Write-Host "==> Committing version bump"
    & git add $versionFile
    & git commit -m "chore: bump version to $Version"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }

    Write-Host "==> Tagging $Version"
    & git tag $Version
    if ($LASTEXITCODE -ne 0) { throw "git tag failed" }

    Write-Host "==> Pushing tag $Version"
    & git push origin $Version
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }

    $noUncommittedChanges = $true
    $allPassed = $true
} finally {
    Write-Host "==> Release summary for $Version"
    Write-Host "version bump committed: $noUncommittedChanges"
    Write-Host "tests passed: $testPassed"
    Write-Host "quality passed: $qualityPassed"
    Write-Host "all passed: $allPassed"

    if (-not $allPassed) {
        if ($noUncommittedChanges) {
            Write-Host "Running cleanup: removing tag and reverting version file"
            & git tag -d $Version 2>$null
            & git revert --no-commit HEAD 2>$null
            & git checkout -- $versionFile
            & git reset --hard HEAD 2>$null
            Write-Host "Cleanup complete."
        } else {
            Write-Host "Reverting version file before exit"
            & git checkout -- $versionFile
            Write-Host "Version file restored."
        }
    }
}

if (-not $allPassed) {
    Write-Output "Release failed for $Version. See summary above."
    exit 1
}

Write-Host "Release $Version queued successfully on origin/master."
