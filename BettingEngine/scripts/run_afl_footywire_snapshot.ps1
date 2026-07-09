# run_afl_footywire_snapshot.ps1
# Weekly Footywire T2 style snapshot — keeps prepare_afl_round.py style data fresh.
# Installed as Task Scheduler job "BetMate AFL Footywire T2 Snapshot" (Tuesday 16:05,
# before AFL Round Prep at 16:20). Added 2026-07-09 after the R18 pricing was found
# silently running T2 on an R9 (May 12) snapshot — nothing was feeding this file.
#
# Round label is auto-detected by the scraper (max games played + 1).

$ErrorActionPreference = "Continue"
$engine = "C:\Users\ElliotBladen\Apps\BettingEngine"
$logDir = Join-Path $engine "outputs\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$log = Join-Path $logDir "afl_footywire_snapshot.log"

$env:PYTHONUTF8 = "1"
$season = (Get-Date).Year

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] Footywire T2 snapshot starting (season $season)" | Add-Content $log
& "$engine\.venv\Scripts\python.exe" "$engine\scripts\scrape_footywire_round_snapshot.py" --season $season --overwrite 2>&1 |
    ForEach-Object { "$_" } | Add-Content $log
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] Done (exit $LASTEXITCODE)" | Add-Content $log
