# git-sync-end.ps1 — run LAST THING before leaving this machine.
#
# Commits everything and pushes, so the other machine always starts from
# the latest state. Pair with git-sync-start.ps1 on arrival.
#
# Also rebuilds the RacingEngine seed when this machine holds racing data the
# seed does not. The 18.5GB DB never travels; the ~52MB seed does, and it is
# useless if it is not rebuilt after racing work.
#
# Usage:  & <repo>\scripts\git-sync-end.ps1 "what happened"   (path-independent)

param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = "Stop"
# Repo root is the parent of scripts/ — works on every machine.
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== BetMate sync-end ===" -ForegroundColor Cyan

# Rebuild the racing seed if this machine is ahead of it (exit code 2).
python scripts/racing_seed_status.py
if ($LASTEXITCODE -eq 2) {
    Write-Host ""
    Write-Host "Rebuilding RacingEngine seed so the racing data travels..." -ForegroundColor Cyan
    python RacingEngine/build_seed.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Seed rebuild FAILED — fix before pushing, or the other machine gets stale data." -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

$dirty = git status --porcelain
if (-not $dirty) {
    Write-Host "Nothing to commit."
} else {
    git add -A
    git commit -m "$Message"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Commit failed — fix and re-run." -ForegroundColor Red
        exit 1
    }
}

git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "PUSH REJECTED — origin has commits this machine does not." -ForegroundColor Red
    Write-Host "The other machine pushed since you started. Run git-sync-start.ps1" -ForegroundColor Yellow
    Write-Host "to fast-forward (your commit is safe locally), then push again."
    exit 1
}

Write-Host "Pushed. Safe to switch machines." -ForegroundColor Green
