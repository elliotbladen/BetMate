param(
    [int]$Season = 2026,
    [string]$TaskName = "BettingEngine NRL Thursday Pricing",
    [string]$RunTime = "18:00",
    [string]$VenvPython = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not $VenvPython) {
    $VenvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPython)) {
    throw "Python not found at $VenvPython."
}

$scriptPath = Join-Path $repoRoot "scripts\run_nrl_pricing.ps1"
$argument   = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At $RunTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Final NRL pricing release every Thursday at $RunTime, including Baz context." `
    -Force

Write-Host "Installed: $TaskName"
Write-Host "Schedule : every Thursday at $RunTime"
Write-Host "Command  : powershell.exe $argument"
