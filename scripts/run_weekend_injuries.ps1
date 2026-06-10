$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8   = "1"

Set-Location $env:BETMATE_ROOT

$uv = "C:\Users\ElliotBladen\.local\bin\uv.exe"

# Step 1: scrape fresh injuries, diff against last known, update latest-injuries.json
Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- Step 1: weekend injury diff (NRL + AFL)"

& $uv run --with requests --with beautifulsoup4 `
    python scrapers\weekend_injury_diff.py --sport both --season 2026

if ($LASTEXITCODE -ne 0) {
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- ERROR: weekend_injury_diff exited $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Step 2: rebuild team news injury section from fresh data, push to Supabase
Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- Step 2: update team news injuries"

& $uv run --with requests `
    python scripts\update_team_news_injuries.py --sport both --season 2026

if ($LASTEXITCODE -ne 0) {
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- ERROR: update_team_news_injuries exited $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- Done. Team news updated and pushed to Supabase."
