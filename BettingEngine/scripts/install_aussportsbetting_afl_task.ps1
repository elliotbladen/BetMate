param(
    [string]$TaskName = "BettingEngine AusSportsBetting AFL Download",
    [string]$RunTime = "09:02",
    [string]$UvExe = "uv"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$scriptPath = Join-Path $repoRoot "scripts\fetch_aussportsbetting_nrl.py"

if (-not (Test-Path $scriptPath)) {
    throw "Could not find AusSportsBetting downloader at $scriptPath"
}

$argument = "run --with playwright python `"$scriptPath`" --page-url https://www.aussportsbetting.com/data/historical-afl-results-and-odds-data/ --output-dir outputs\afl_weekly_review\historical --headless true"
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
    -Description "Downloads the latest AusSportsBetting AFL 2009-present results and odds workbook every Tuesday at $RunTime." `
    -Force

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule : every Tuesday at $RunTime"
Write-Host "Command  : $UvExe $argument"
Write-Host "Output   : outputs\afl_weekly_review\historical\latest.xlsx"
