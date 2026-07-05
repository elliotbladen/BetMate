param(
    [string]$TaskName = "BettingEngine Running CLV Summary",
    [string]$RunTime = "09:15",
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

$scriptPath = Join-Path $repoRoot "scripts\rolling_clv_summary.py"

if (-not (Test-Path $scriptPath)) {
    throw "Could not find rolling CLV summary script at $scriptPath"
}

$argument = "`"$scriptPath`" --sport ALL"
$action   = New-ScheduledTaskAction -Execute $PythonExe -Argument $argument -WorkingDirectory $repoRoot
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At $RunTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Builds running NRL/AFL round-by-round and rolling CLV summary every Tuesday at $RunTime." `
    -Force

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule : every Tuesday at $RunTime"
Write-Host "Command  : $PythonExe $argument"
Write-Host "Output   : outputs\clv_running\running_clv_summary.csv"
