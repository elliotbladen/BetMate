# install_afl_home_away_task.ps1
#
# Installs "BetMate AFL Home Away Value" to run every Monday at 08:10.
# Scrapes aussportstipping.com home advantage table (rolling 1-year window)
# and writes latest-home-away.json so the odds page H/A Value badges are fresh.
#
# H/A venue data moves slowly — weekly refresh is sufficient.
# StartWhenAvailable: fires on wake if the machine was asleep at 08:10 Monday.
# Run once (as admin if needed) to install. Re-run to update.

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$wrapper  = Join-Path $repoRoot "scripts\run_bvi_home_away.ps1"
$script   = Join-Path $repoRoot "scrapers\afl_home_advantage.py"

if (-not (Test-Path $wrapper)) { throw "Wrapper not found at $wrapper" }
if (-not (Test-Path $script))  { throw "Scraper not found at $script" }

$action = New-ScheduledTaskAction `
    -Execute          "powershell.exe" `
    -Argument         "-NonInteractive -File `"$wrapper`" `"$script`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At "08:10"

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
    -TaskName   "BetMate AFL Home Away Value" `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Scrapes AFL home/away win% from aussportstipping.com weekly (Monday 08:10). Rolling 1-year window. Writes data/afl/home-away/processed/latest-home-away.json." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "BetMate AFL Home Away Value"
Write-Host ""
Write-Host "Installed: BetMate AFL Home Away Value"
Write-Host "  Trigger  : Monday 08:10 weekly (StartWhenAvailable)"
Write-Host "  Retries  : 2x on failure, 15 min apart"
Write-Host "  Next run : $($info.NextRunTime)"
Write-Host "  Script   : $script"
