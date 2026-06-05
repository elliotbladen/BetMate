$taskName  = "BetMate NRL Predictions Push"
$script    = "C:\Users\ElliotBladen\Apps\scripts\run_push_nrl_predictions.ps1"
$logDir    = "C:\Users\ElliotBladen\Apps\data\logs"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName   $taskName `
    -Action     (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -WindowStyle Hidden -File `"$script`" >> `"$logDir\nrl_predictions_task.log`" 2>&1" -WorkingDirectory "C:\Users\ElliotBladen\Apps") `
    -Trigger    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At "09:00") `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Push NRL model predictions to JSON + Supabase every Thursday at 09:00"

Write-Host ""
Write-Host "Installed: '$taskName' -- Thursday 09:00"
