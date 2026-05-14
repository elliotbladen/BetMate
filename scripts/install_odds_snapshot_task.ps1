# install_odds_snapshot_task.ps1
#
# Installs BetMate Odds Snapshot to run three times daily (09:00, 12:00, 18:00).
# StartWhenAvailable: if the machine was off/asleep at the scheduled time,
# the task fires as soon as it comes back online.
# RestartCount: Task Scheduler retries twice (30 min apart) if the cycle fails.
# The Python script retries up to 3x (5 min apart) on network failure.
#
# Run once (as admin if needed) to install. Re-run to update.

$ErrorActionPreference = "Stop"

$uvExe    = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runner   = Join-Path $repoRoot "scripts\run_odds_snapshot_cycle.ps1"

if (-not (Test-Path $runner)) { throw "Cannot find $runner" }

# Remove old tasks
foreach ($old in @("BetMate Odds Snapshot 10min", "BetMate Daily Odds Snapshot")) {
    if (Get-ScheduledTask -TaskName $old -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $old -Confirm:$false
        Write-Host "Removed: $old"
    }
}

$action = New-ScheduledTaskAction `
    -Execute          "powershell.exe" `
    -Argument         "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -UvExe `"$uvExe`"" `
    -WorkingDirectory $repoRoot

# Morning open, midday, pre-game evening
$t1 = New-ScheduledTaskTrigger -Daily -At "09:00"
$t2 = New-ScheduledTaskTrigger -Daily -At "12:00"
$t3 = New-ScheduledTaskTrigger -Daily -At "18:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit    (New-TimeSpan -Minutes 30) `
    -MultipleInstances     IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount          2 `
    -RestartInterval       (New-TimeSpan -Minutes 30)

$principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -LogonType Interactive `
    -RunLevel  Highest

Register-ScheduledTask `
    -TaskName  "BetMate Odds Snapshot" `
    -Action    $action `
    -Trigger   @($t1, $t2, $t3) `
    -Settings  $settings `
    -Principal $principal `
    -Description "NRL + AFL odds snapshot 3x daily (09:00, 12:00, 18:00). Retries 2x on failure (30 min apart). Catches up missed runs on wake." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "BetMate Odds Snapshot"
Write-Host ""
Write-Host "Installed: BetMate Odds Snapshot"
Write-Host "  Triggers : 09:00 + 12:00 + 18:00 daily (StartWhenAvailable)"
Write-Host "  Retries  : 2x on failure, 30 min apart"
Write-Host "  Next run : $($info.NextRunTime)"
Write-Host "  Script   : $runner"
