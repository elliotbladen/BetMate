param(
    [string]$UvExe = "C:\Users\ElliotBladen\.local\bin\uv.exe"
)

$ErrorActionPreference = "Continue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$snapshotScript = Join-Path $repoRoot "scrapers\odds_snapshot.py"
$trackerScript = Join-Path $repoRoot "scrapers\odds_movement_tracker.py"
$env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
$logDir = Join-Path $repoRoot "data\odds_snapshots\logs"
$cycleLog = Join-Path $logDir "cycle.log"

Set-Location $repoRoot

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Add-Content -Path $cycleLog -Value ""
Add-Content -Path $cycleLog -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting odds snapshot cycle"
Add-Content -Path $cycleLog -Value "Repo root: $repoRoot"
Add-Content -Path $cycleLog -Value "Snapshot script: $snapshotScript"
Add-Content -Path $cycleLog -Value "Tracker script: $trackerScript"

if (-not (Test-Path $snapshotScript)) {
    Add-Content -Path $cycleLog -Value "Missing snapshot script: $snapshotScript"
    throw "Missing snapshot script: $snapshotScript"
}

if (-not (Test-Path $trackerScript)) {
    Add-Content -Path $cycleLog -Value "Missing tracker script: $trackerScript"
    throw "Missing tracker script: $trackerScript"
}

& $UvExe run $snapshotScript
if ($LASTEXITCODE -ne 0) {
    $msg = "Snapshot script failed with exit code $LASTEXITCODE"
    Add-Content -Path $cycleLog -Value $msg

    # Windows toast notification so the failure is visible
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>BetMate - snapshot failed</text><text>Odds arrows won't update. Check cycle.log.</text></binding></visual></toast>")
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("BetMate").Show($toast)
    } catch {}

    exit $LASTEXITCODE
}

& $UvExe run $trackerScript
Add-Content -Path $cycleLog -Value "Tracker script finished with exit code $LASTEXITCODE"
exit $LASTEXITCODE
