# Start Baz brain + ngrok tunnel
# Run this from a regular PowerShell window to bring Baz online on Vercel

$ErrorActionPreference = 'SilentlyContinue'

# 1. Start baz_server if not already running
$baz = Get-Process python | Where-Object { $_.CommandLine -like "*baz_server*" }
if (-not $baz) {
    Write-Host "Starting Baz brain..." -ForegroundColor Cyan
    Start-Process -FilePath "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
        -ArgumentList "C:\Users\ElliotBladen\Apps\BettingEngine\baz_server.py" `
        -WindowStyle Minimized
    Start-Sleep -Seconds 4
}

# 2. Start ngrok tunnel
Write-Host "Starting ngrok tunnel..." -ForegroundColor Cyan
Start-Process -FilePath "ngrok" `
    -ArgumentList "http --domain=aim-basil-juror.ngrok-free.app 8765" `
    -WindowStyle Minimized

Start-Sleep -Seconds 5

# 3. Health check
try {
    $r = Invoke-RestMethod -Uri "https://aim-basil-juror.ngrok-free.app/health" -TimeoutSec 10
    Write-Host "Baz is ONLINE via tunnel: $($r.status)" -ForegroundColor Green
} catch {
    Write-Host "Tunnel not ready - check ngrok dashboard at http://127.0.0.1:4040" -ForegroundColor Yellow
}
