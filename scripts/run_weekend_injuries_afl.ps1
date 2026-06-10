$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8   = "1"
Set-Location $env:BETMATE_ROOT
$uv = "C:\Users\ElliotBladen\.local\bin\uv.exe"

# Runs Monday 15:00 — Footywire AFL injury list updates by Monday afternoon.
# (Fox Sports match reports are now JS-rendered, replaced with Footywire.)

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- AFL: scraping Footywire injury list"
& $uv run --with requests --with beautifulsoup4 `
    python scrapers\weekend_injury_diff.py --sport AFL --season 2026

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- AFL: updating team news"
& $uv run --with requests `
    python scripts\update_team_news_injuries.py --sport AFL --season 2026

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- Done."
