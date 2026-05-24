# install_nrl_bvi_task.ps1
#
# Installs "BetMate NRL BVI" to run every Monday at 08:20.
# Scrapes aussportstipping.com NRL BVI (rolling 1-year window) and writes
# latest-bvi.json so the odds page BVI badges are fresh each week.
#
# StartWhenAvailable: fires on wake if the machine was asleep at 08:20 Monday.
# Run once (as admin if needed) to install. Re-run to update.

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$wrapper  = Join-Path $repoRoot "scripts\run_bvi_home_away.ps1"
$script   = Join-Path $repoRoot "scrapers\nrl_bvi.py"

if (-not (Test-Path $wrapper)) { throw "Wrapper not found at $wrapper" }
if (-not (Test-Path $script))  { throw "Scraper not found at $script" }

$action = New-ScheduledTaskAction `
    -Execute          "powershell.exe" `
    -Argument         "-NonInteractive -File `"$wrapper`" `"$script`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At "08:20"

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
    -TaskName   "BetMate NRL BVI" `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Scrapes NRL Betting Value Index from aussportstipping.com weekly (Monday 08:20). Rolling 1-year window. Writes data/nrl/bvi/processed/latest-bvi.json. Catches up missed runs on wake." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "BetMate NRL BVI"
Write-Host ""
Write-Host "Installed: BetMate NRL BVI"
Write-Host "  Trigger  : Monday 08:20 weekly (StartWhenAvailable)"
Write-Host "  Retries  : 2x on failure, 15 min apart"
Write-Host "  Next run : $($info.NextRunTime)"
Write-Host "  Script   : $script"
