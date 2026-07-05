param(
    [int]$Season = 2026,
    [string]$TaskName = "BettingEngine NRL Results Fetch",
    [string]$RunTime = "09:00",
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

$scriptPath = Join-Path $repoRoot "scripts\fetch_nrl_results.py"

# --round 0 = auto-detect all rounds missing results in DB
$argument = "`"$scriptPath`" --season $Season --round 0"

$action   = New-ScheduledTaskAction -Execute $VenvPython -Argument $argument -WorkingDirectory $repoRoot
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $RunTime
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
    -Description "Fetches NRL round results from NRL.com every Monday at $RunTime and loads them into the BettingEngine DB. Runs before the 7PM pricing run so ELO is up to date." `
    -Force

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule : every Monday at $RunTime"
Write-Host "Python   : $VenvPython"
Write-Host "Command  : $VenvPython $argument"
Write-Host ""
Write-Host "To run manually now:"
Write-Host "  cd $repoRoot"
Write-Host "  $VenvPython scripts\fetch_nrl_results.py --season $Season"
Write-Host ""
Write-Host "To test without writing to DB:"
Write-Host "  $VenvPython scripts\fetch_nrl_results.py --season $Season --dry-run"
