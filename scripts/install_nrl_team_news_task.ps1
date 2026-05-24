# install_nrl_team_news_task.ps1
#
# Installs "BetMate NRL Team News" to run every Tuesday at 10:30.
# Reads latest-injuries.json (scraped at 10:00) and auto-generates the
# injuries section of data/nrl/team-news/latest.json, preserving any
# manually-entered suspension items. Then pushes to Supabase.
#
# Run once (as admin if needed) to install. Re-run to update.

$ErrorActionPreference = "Stop"

$uvExe    = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$script   = Join-Path $repoRoot "scrapers\nrl_team_news.py"

if (-not (Test-Path $uvExe))  { throw "uv not found at $uvExe" }
if (-not (Test-Path $script)) { throw "Scraper not found at $script" }

$action = New-ScheduledTaskAction `
    -Execute          $uvExe `
    -Argument         "run --with tzdata --with requests python `"$script`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Tuesday -At "10:30"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit    (New-TimeSpan -Minutes 5) `
    -MultipleInstances     IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount          2 `
    -RestartInterval       (New-TimeSpan -Minutes 10)

$principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -LogonType Interactive `
    -RunLevel  Limited

Register-ScheduledTask `
    -TaskName   "BetMate NRL Team News" `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Auto-generates NRL team news injuries from latest-injuries.json (Tuesday 10:30, 30 min after injuries scraper). Preserves manual suspension items. Pushes to Supabase." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "BetMate NRL Team News"
Write-Host ""
Write-Host "Installed: BetMate NRL Team News"
Write-Host "  Trigger  : Tuesday 10:30 weekly (StartWhenAvailable)"
Write-Host "  Retries  : 2x on failure, 10 min apart"
Write-Host "  Next run : $($info.NextRunTime)"
Write-Host "  Script   : $script"
