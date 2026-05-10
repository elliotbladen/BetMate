param(
    [string]$TaskName = "BettingEngine NRL Referees Fetch",
    [string]$UvExe = "C:\Users\ElliotBladen\.local\bin\uv.exe",
    [string]$RunTime = "12:00",
    [int]$Season = 2026
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$scriptPath = Join-Path $repoRoot "lib\scraper\nrl_referees.py"
$runnerPath = Join-Path $repoRoot "scripts\run_nrl_referees.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "Could not find referee scraper at $scriptPath"
}

if (-not (Test-Path $runnerPath)) {
    throw "Could not find referee runner at $runnerPath"
}

if (-not (Test-Path $UvExe)) {
    throw "Could not find uv executable at $UvExe"
}

$argument = "-NoProfile -ExecutionPolicy Bypass -File `"scripts\run_nrl_referees.ps1`" -UvExe `"$UvExe`" -Season $Season"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At $RunTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Scrapes NRL referee appointments into BetMATE every Wednesday at $RunTime." `
    -Force

Write-Host "Installed: $TaskName"
Write-Host "Schedule:  Wednesday at $RunTime"
Write-Host "Output:    data/nrl/referees/processed/latest-referees.csv"
