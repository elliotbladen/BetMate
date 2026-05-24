param(
    [string]$TaskName = "BettingEngine NRL Referees Fetch",
    [string]$UvExe = "C:\Users\ElliotBladen\.local\bin\uv.exe",
    [int]$Season = 2026
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$scriptPath = Join-Path $repoRoot "scrapers\nrl_referees.py"
$runnerPath = Join-Path $repoRoot "scripts\run_nrl_referees.ps1"

if (-not (Test-Path $scriptPath)) { throw "Could not find referee scraper at $scriptPath" }
if (-not (Test-Path $runnerPath)) { throw "Could not find referee runner at $runnerPath" }
if (-not (Test-Path $UvExe))      { throw "Could not find uv executable at $UvExe" }

$argument = "-NoProfile -ExecutionPolicy Bypass -File `"scripts\run_nrl_referees.ps1`" -UvExe `"$UvExe`" -Season $Season"
$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot

$trigger1 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At "14:00"
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At "17:00"
$trigger3 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At "08:00"
$trigger4 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At "12:00"
$trigger5 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At "17:00"
$trigger6 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At "08:00"
$trigger7 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At "12:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($trigger1, $trigger2, $trigger3, $trigger4, $trigger5, $trigger6, $trigger7) `
    -Settings $settings `
    -Description "Scrapes NRL referee appointments Tuesday-Thursday until official match-centre data is available. Writes latest-referees.csv for BettingEngine T6." `
    -Force

Write-Host "Installed: $TaskName"
Write-Host "Schedule:  Tuesday 14:00 + 17:00; Wednesday 08:00 + 12:00 + 17:00; Thursday 08:00 + 12:00 (weekly)"
Write-Host "Output:    data/nrl/referees/processed/latest-referees.csv"
