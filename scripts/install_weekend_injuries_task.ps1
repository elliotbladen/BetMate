# Installs two injury diff tasks:
#   "BetMate NRL Weekend Injuries" — Monday 07:30
#   "BetMate AFL Weekend Injuries" — Wednesday 09:00 (footywire updates Tue/Wed after training)

$logDir = "C:\Users\ElliotBladen\Apps\data\injuries\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

# ---- NRL: Monday 07:30 ----
$nrlTask    = "BetMate NRL Weekend Injuries"
$nrlScript  = "C:\Users\ElliotBladen\Apps\scripts\run_weekend_injuries_nrl.ps1"
$nrlLog     = "$logDir\nrl_task_output.log"

if (Get-ScheduledTask -TaskName $nrlTask -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $nrlTask -Confirm:$false
}
Register-ScheduledTask `
    -TaskName   $nrlTask `
    -Action     (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -WindowStyle Hidden -File `"$nrlScript`" >> `"$nrlLog`" 2>&1" -WorkingDirectory "C:\Users\ElliotBladen\Apps") `
    -Trigger    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "07:30") `
    -Settings   $settings `
    -Principal  $principal `
    -Description "NRL weekend injury diff + team news push (Monday - NRL casualty ward updates Sun/Mon)"

# ---- AFL: Wednesday 09:00 ----
$aflTask    = "BetMate AFL Weekend Injuries"
$aflScript  = "C:\Users\ElliotBladen\Apps\scripts\run_weekend_injuries_afl.ps1"
$aflLog     = "$logDir\afl_task_output.log"

if (Get-ScheduledTask -TaskName $aflTask -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $aflTask -Confirm:$false
}
Register-ScheduledTask `
    -TaskName   $aflTask `
    -Action     (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -WindowStyle Hidden -File `"$aflScript`" >> `"$aflLog`" 2>&1" -WorkingDirectory "C:\Users\ElliotBladen\Apps") `
    -Trigger    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At "09:00") `
    -Settings   $settings `
    -Principal  $principal `
    -Description "AFL weekend injury diff + team news push (Wednesday - footywire updates after Tue/Wed training)"

Write-Host ""
Write-Host "Installed:"
Write-Host "  '$nrlTask'  -- Monday 07:30"
Write-Host "  '$aflTask'  -- Wednesday 09:00"
