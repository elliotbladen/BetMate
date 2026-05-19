# install_afl_bvi_task.ps1
#
# Installs "BetMate AFL BVI" to run every Monday at 08:00.
# Scrapes aussportstipping.com and writes latest-bvi.json so the odds page
# BVI badges are fresh each week.
#
# StartWhenAvailable: fires on wake if the machine was asleep at 08:00 Monday.
# Run once (as admin if needed) to install. Re-run to update.

$ErrorActionPreference = "Stop"

$uvExe    = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$script   = Join-Path $repoRoot "lib\scraper\afl_bvi.py"

if (-not (Test-Path $uvExe))  { throw "uv not found at $uvExe" }
if (-not (Test-Path $script)) { throw "Scraper not found at $script" }

$action = New-ScheduledTaskAction `
    -Execute          $uvExe `
    -Argument         "run --with requests --with beautifulsoup4 python `"$script`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At "08:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit    (New-TimeSpan -Minutes 10) `
    -MultipleInstances     IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount          2 `
    -RestartInterval       (New-TimeSpan -Minutes 15)

$principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -LogonType Interactive `
    -RunLevel  Limited

Register-ScheduledTask `
    -TaskName   "BetMate AFL BVI" `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Scrapes AFL Betting Value Index from aussportstipping.com weekly (Monday 08:00). Writes data/afl/bvi/processed/latest-bvi.json. Catches up missed runs on wake." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "BetMate AFL BVI"
Write-Host ""
Write-Host "Installed: BetMate AFL BVI"
Write-Host "  Trigger  : Monday 08:00 weekly (StartWhenAvailable)"
Write-Host "  Retries  : 2x on failure, 15 min apart"
Write-Host "  Next run : $($info.NextRunTime)"
Write-Host "  Script   : $script"
