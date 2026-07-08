# install_afl_r15_thursday_task.ps1
# Run this ONCE as admin to register the Thursday 14:10 reprice task
# Right-click PowerShell -> Run as Administrator, then:
#   & "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\install_afl_r15_thursday_task.ps1"

$taskName = "BetMate AFL R15 Thursday Reprice"
$script   = "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_afl_r15_thursday_reprice.ps1"

$action   = New-ScheduledTaskAction -Execute "powershell.exe" `
                -Argument "-NonInteractive -WindowStyle Hidden -File `"$script`""

$trigger  = New-ScheduledTaskTrigger -Once -At "2026-06-18T14:10:00"

$settings = New-ScheduledTaskSettingsSet `
                -StartWhenAvailable `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
                -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName  $taskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -RunLevel  Highest `
    -Force | Out-Null

Write-Host "Task registered: $taskName"
Write-Host "Fires: Thursday 18 June 2026 at 14:10 (10 minutes after squad drop)"
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
