# git-sync-end.ps1 — run LAST THING before leaving this machine.
#
# Commits everything and pushes, so the other machine always starts from
# the latest state. Pair with git-sync-start.ps1 on arrival.
#
# Usage:  & C:\Users\ElliotBladen\Apps\scripts\git-sync-end.ps1 "short description of the session"

param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = "Stop"
Set-Location "C:\Users\ElliotBladen\Apps"

Write-Host "=== BetMate sync-end ===" -ForegroundColor Cyan

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
