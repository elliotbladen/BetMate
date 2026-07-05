param(
    [string]$TaskName = "BettingEngine AFL Weekly ML CLV Report",
    [string]$RunTime = "09:10",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not $PythonExe) {
    $PythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
}

if (-not (Test-Path $PythonExe)) {
    throw "Python not found at $PythonExe. Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
}

$scriptPath = Join-Path $repoRoot "scripts\afl_weekly_ml_clv_report.py"

if (-not (Test-Path $scriptPath)) {
    throw "Could not find AFL CLV report script at $scriptPath"
}

$argument = "`"$scriptPath`" --season 2026 --round 0"
$action   = New-ScheduledTaskAction -Execute $PythonExe -Argument $argument -WorkingDirectory $repoRoot
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
    -Description "Compares latest completed AFL round normal engine, ML shadow, and market CLV every Tuesday at $RunTime. Saves under outputs\afl_weekly_review\reports." `
    -Force

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule : every Tuesday at $RunTime"
Write-Host "Command  : $PythonExe $argument"
Write-Host "Output   : outputs\afl_weekly_review\reports\r{round}_afl_ml_clv_comparison_2026.csv"
