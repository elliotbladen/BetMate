# Start Baz brain + Cloudflare tunnel
# Called by Task Scheduler on logon

$ErrorActionPreference = 'SilentlyContinue'

# Kill any stale instances
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# 1. Start Baz FastAPI server
$bazRunning = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
if (-not $bazRunning) {
    Write-Host "Starting Baz brain..."
    Start-Process `
        -FilePath "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
        -ArgumentList "C:\Users\ElliotBladen\Apps\BettingEngine\baz_server.py" `
        -WindowStyle Minimized
    Start-Sleep -Seconds 5
}

# 2. Start Cloudflare tunnel (betmate-baz → baz.betmate.au → localhost:8765)
Write-Host "Starting Cloudflare tunnel..."
Start-Process `
    -FilePath "C:\Program Files (x86)\cloudflared\cloudflared.exe" `
    -ArgumentList "tunnel run betmate-baz" `
    -WindowStyle Minimized

Start-Sleep -Seconds 8

# 3. Health check
try {
    $r = Invoke-RestMethod -Uri "https://baz.betmate.au/health" -TimeoutSec 10
    Write-Host "Baz ONLINE: $($r.status)"
} catch {
    Write-Host "Baz tunnel not ready - check cloudflared logs"
}
