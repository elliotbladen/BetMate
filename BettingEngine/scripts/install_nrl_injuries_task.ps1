param(
    [int]$Season = 2026,
    [string]$TaskName = "BettingEngine NRL Injuries Fetch",
    [string]$RunTime = "10:00",
    [string]$UvExe = ""
)

$ErrorActionPreference = "Stop"

$betmateRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\BetMate")

if (-not $UvExe) {
    $UvExe = "$env:USERPROFILE\.local\bin\uv.exe"
}

if (-not (Test-Path $UvExe)) {
    throw "uv not found at $UvExe. Install from https://docs.astral.sh/uv/"
}

$scraperRelPath = "lib\scraper\nrl_injuries.py"
$argument = "run --with requests --with beautifulsoup4 python `"$scraperRelPath`" --season $Season"

$action   = New-ScheduledTaskAction -Execute $UvExe -Argument $argument -WorkingDirectory $betmateRoot
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
    -Description "Scrapes NRL injury data from NRL.com casualty ward every Monday at $RunTime. Writes to BetMate latest-injuries.json for use by the Monday 7PM pricing run." `
    -Force

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Schedule  : every Monday at $RunTime"
Write-Host "uv        : $UvExe"
Write-Host "Directory : $betmateRoot"
Write-Host "Command   : uv $argument"
Write-Host ""
Write-Host "To run manually now:"
Write-Host "  cd $betmateRoot"
Write-Host "  $UvExe run --with requests --with beautifulsoup4 python lib\scraper\nrl_injuries.py --season $Season"
