# install_nrl_emotional_task.ps1
# Installs a Task Scheduler task that runs nrl_emotional.py every Tuesday at 11:00.
# This fires after the injury scraper (Monday 10:00) so injuries are fresh.
# BettingEngine's prepare_round.py (Tuesday 19:00) then picks up latest-emotional.json.
#
# Usage: Run once as Administrator:
#   powershell -ExecutionPolicy Bypass -File scripts\install_nrl_emotional_task.ps1

$TaskName   = "BetMate NRL Emotional Flags"
$UvPath     = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$ScriptPath = "C:\Users\ElliotBladen\Apps\lib\scraper\nrl_emotional.py"
$WorkDir    = "C:\Users\ElliotBladen\Apps"
$LogFile    = "C:\Users\ElliotBladen\Apps\data\nrl\emotional\logs\task.log"

$Args = "run --with anthropic --with requests python `"$ScriptPath`" --round 0 >> `"$LogFile`" 2>&1"

$Action  = New-ScheduledTaskAction -Execute $UvPath -Argument $Args -WorkingDirectory $WorkDir
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At "11:00AM"
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -Settings $Settings `
    -Description "Generates T7 emotional flags for upcoming NRL round via BetMate/Baz (Claude API)" `
    -Force

Write-Host ""
Write-Host "Task '$TaskName' installed — runs every Tuesday at 11:00 AM."
Write-Host "BettingEngine prepare_round.py will auto-load latest-emotional.json."
Write-Host ""
Write-Host "To test manually:"
Write-Host "  uv run --with anthropic --with requests python lib\scraper\nrl_emotional.py --round 11 --dry-run"
