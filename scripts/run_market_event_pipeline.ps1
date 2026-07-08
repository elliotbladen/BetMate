param(
    [string]$UvExe = "C:\Users\ElliotBladen\.local\bin\uv.exe",
    [int]$Season = 2026
)

$ErrorActionPreference = "Continue"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$logDir = Join-Path $repoRoot "data\market_events\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "pipeline.log"

Add-Content -Path $log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting market event pipeline"

& $UvExe run python "scripts\build_market_event_log.py" --season $Season 2>&1 | Add-Content -Path $log
& $UvExe run python "scripts\compute_snapshot_deltas.py" --season $Season 2>&1 | Add-Content -Path $log
& $UvExe run python "scripts\tag_odds_movements.py" --season $Season 2>&1 | Add-Content -Path $log

Add-Content -Path $log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Finished market event pipeline"
