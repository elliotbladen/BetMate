# Run this from an elevated PowerShell (right-click → Run as Administrator)
# Changes all BetMate/BettingEngine tasks from Interactive to S4U
# so they fire whether or not you're logged in at the time

$tasks = @(
    "BetMate NRL News Flags",
    "BetMate NRL Postgame Scout",
    "BetMate NRL Round Prep",
    "BetMate NRL Style Stats Scrape",
    "BetMate NRL Historical Results",
    "BetMATE AFL Umpires Fetch",
    "BetMate Odds Snapshot 10min",
    "BettingEngine NRL Referees Fetch",
    "BettingEngine NRL Injuries Fetch",
    "BettingEngine NRL Results Fetch",
    "BettingEngine NRL Pricing",
    "BettingEngine NRL Thursday Pricing",
    "BettingEngine AusSportsBetting NRL Download",
    "BettingEngine AusSportsBetting AFL Download",
    "BettingEngine NRL Weekly CLV Report",
    "BettingEngine NRL Weekly ML CLV Report",
    "BettingEngine AFL Weekly ML CLV Report",
    "BettingEngine Running CLV Summary"
)

foreach ($name in $tasks) {
    try {
        $xml = Export-ScheduledTask -TaskName $name
        $xml = $xml -replace '<LogonType>InteractiveToken</LogonType>', '<LogonType>S4U</LogonType>'
        $xml = $xml -replace '<LogonType>Interactive</LogonType>', '<LogonType>S4U</LogonType>'
        Register-ScheduledTask -TaskName $name -Xml $xml -Force -ErrorAction Stop | Out-Null
        Write-Host "OK  $name"
    } catch {
        Write-Host "ERR $name -- $($_.Exception.Message)"
    }
}

Write-Host "`nDone. Tasks will now run whether or not you are logged in."
