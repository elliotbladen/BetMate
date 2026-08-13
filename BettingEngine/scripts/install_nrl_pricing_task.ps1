param(
    [int]$Season = 2026,
    [string]$TaskName = "BettingEngine NRL Pricing",
    [string]$RunTime = "19:03",
    [string]$VenvPython = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not $VenvPython) {
    $VenvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPython)) {
    throw "Python not found at $VenvPython. Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
}

$scriptPath = Join-Path $repoRoot "scripts\run_nrl_pricing.ps1"
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Run the release wrapper, not prepare_round.py directly: it prices, exports,
# pushes matrices, and publishes Baz's current context as one deployment.
$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $RunTime
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
    -Description "Runs and publishes BettingEngine NRL pricing every Monday at $RunTime, including Baz context." `
    -Force

Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule: every Monday at $RunTime"
Write-Host "Command: powershell.exe $argument"
