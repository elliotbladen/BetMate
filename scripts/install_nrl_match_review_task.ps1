# install_nrl_match_review_task.ps1
#
# Installs "BetMate NRL Match Review" to run every Monday at 09:30.
# Scrapes NRL MRC judiciary charges + fresh injuries (diff vs prior week).
# Output: data/nrl/match-review/latest.json
#
# Run once (as admin if needed) to install. Re-run to update.

$ErrorActionPreference = "Stop"

$repoRoot   = "C:\Users\ElliotBladen\Apps"
$wrapper    = Join-Path $repoRoot "scripts\run_nrl_match_review.ps1"
$scraper    = Join-Path $repoRoot "scrapers\nrl_match_review.py"

if (-not (Test-Path $wrapper)) { throw "Wrapper not found at $wrapper" }
if (-not (Test-Path $scraper)) { throw "Scraper not found at $scraper" }

$action = New-ScheduledTaskAction `
    -Execute          "powershell.exe" `
    -Argument         "-NonInteractive -File `"$wrapper`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At "09:30"

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
    -TaskName   "BetMate NRL Match Review" `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Monday 09:30 — NRL MRC charges + fresh injury diff vs prior week. Writes data/nrl/match-review/latest.json." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "BetMate NRL Match Review"
Write-Host ""
Write-Host "Installed: BetMate NRL Match Review"
Write-Host "  Trigger : Monday 09:30 weekly (StartWhenAvailable)"
Write-Host "  Retries : 2x on failure, 15 min apart"
Write-Host "  Next run: $($info.NextRunTime)"
Write-Host "  Output  : $repoRoot\data\nrl\match-review\latest.json"
