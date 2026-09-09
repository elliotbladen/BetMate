# git-sync-start.ps1 — run FIRST THING when starting work on this machine.
#
# Protects against the 2026-07-08 incident: two machines editing the same repo
# with uncommitted work on both sides, silently overwriting each other.
#
# What it does:
#   1. Refuses to pull if the working tree is dirty (you decide: commit or stash)
#   2. Fetches origin and shows how far ahead/behind you are
#   3. Checks the RacingEngine seed against your local DB (the DB never
#      travels through git — only the ~52MB seed does)
#   4. Pulls with --ff-only — it will NEVER auto-merge diverged histories.
#      If it refuses, this machine and the other machine both committed since
#      the last sync. Fix by reconciling deliberately, not by `git pull` alone.
#
# Usage:  & <repo>\scripts\git-sync-start.ps1        (path-independent)

$ErrorActionPreference = "Stop"
# Repo root is the parent of scripts/ — works on every machine.
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== BetMate sync-start ===" -ForegroundColor Cyan

# 1. Dirty check
$dirty = git status --porcelain | Where-Object { $_ -notmatch "^\?\?" }
if ($dirty) {
    Write-Host ""
    Write-Host "STOP: uncommitted changes on this machine:" -ForegroundColor Red
    $dirty | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Commit them first (git-sync-end.ps1), then re-run this script." -ForegroundColor Yellow
    Write-Host "Do NOT pull over uncommitted work — that is how the July 8 mess happened."
    exit 1
}

# 2. Fetch and report position
git fetch origin
$ahead  = git rev-list --count origin/main..main
$behind = git rev-list --count main..origin/main
Write-Host "Local is $ahead ahead / $behind behind origin/main"

# 3. Fast-forward only
if ([int]$behind -gt 0) {
    git pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "PULL REFUSED — histories have diverged (both machines committed)." -ForegroundColor Red
        Write-Host "Do not force anything. Open a Claude session and say:" -ForegroundColor Yellow
        Write-Host '  "git sync-start says the machines have diverged, reconcile it"'
        exit 1
    }
}

# 4. RacingEngine data check — the DB is gitignored, only the seed travels.
Write-Host ""
python scripts/racing_seed_status.py
$seedState = $LASTEXITCODE
if ($seedState -eq 1) {
    Write-Host ""
    Write-Host "Racing DB is behind the seed. Restore it before any racing work." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Up to date. Safe to work." -ForegroundColor Green
