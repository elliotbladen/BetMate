# Run from elevated PowerShell (Run as Administrator)
# Edits task XML files directly in C:\Windows\System32\Tasks\

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

$taskDir = "C:\Windows\System32\Tasks"

foreach ($name in $tasks) {
    $path = Join-Path $taskDir $name
    if (-not (Test-Path $path)) {
        Write-Host "SKIP $name (file not found)"
        continue
    }
    try {
        $xml = [xml](Get-Content $path -Raw)
        $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
        $ns.AddNamespace("ts", "http://schemas.microsoft.com/windows/2004/02/mit/task")
        $node = $xml.SelectSingleNode("//ts:LogonType", $ns)
        if ($node) {
            $node.InnerText = "S4U"
            $xml.Save($path)
            Write-Host "OK  $name"
        } else {
            Write-Host "SKIP $name (no LogonType node found)"
        }
    } catch {
        Write-Host "ERR $name -- $($_.Exception.Message)"
    }
}

# Reload Task Scheduler service to pick up changes
Stop-Service Schedule -Force
Start-Service Schedule
Write-Host "`nDone. Task Scheduler restarted."
