$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8   = "1"
Set-Location $env:BETMATE_ROOT
$uv = "C:\Users\ElliotBladen\.local\bin\uv.exe"

# Runs Monday 15:00 — Fox Sports Report Card is posted ~early Monday afternoon.
# Reads individual game write-ups for injury mentions.
# Does NOT rely on footywire/AFL injury lists (those update Wed).

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- AFL: scraping Fox Sports match reports"
& $uv run --with requests --with beautifulsoup4 `
    python scrapers\afl_match_reports.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- AFL: updating team news"
& $uv run --with requests `
    python scripts\update_team_news_injuries.py --sport AFL --season 2026

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- Done."
