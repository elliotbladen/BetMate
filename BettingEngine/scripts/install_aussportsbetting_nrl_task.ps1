param(
    [string]$TaskName = "BettingEngine AusSportsBetting NRL Download",
    [string]$UvExe = "uv",
    [string]$RunTime = "09:00",
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$scriptPath = Join-Path $repoRoot "scripts\fetch_aussportsbetting_nrl.py"

if (-not (Test-Path $scriptPath)) {
    throw "Could not find downloader at $scriptPath"
}

$argument = "run --with playwright $PythonExe `"$scriptPath`" --headless true"
$action   = New-ScheduledTaskAction -Execute $UvExe -Argument $argument -WorkingDirectory $repoRoot
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At $RunTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Downloads AusSportsBetting NRL 2009-present historical results and odds workbook every Tuesday at $RunTime. Saves to outputs\nrl_weekly_review\historical\latest.xlsx for score and price review." `
    -Force

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule : every Tuesday at $RunTime"
Write-Host "Command  : $UvExe $argument"
Write-Host "Output   : outputs\nrl_weekly_review\historical\latest.xlsx"
Write-Host ""
Write-Host "To run manually now:"
Write-Host "  cd $repoRoot"
Write-Host "  $UvExe $argument"
