$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8   = "1"
Set-Location $env:BETMATE_ROOT
$uv = "C:\Users\ElliotBladen\.local\bin\uv.exe"

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- NRL weekend injury diff"
& $uv run --with requests --with beautifulsoup4 python scrapers\weekend_injury_diff.py --sport NRL --season 2026
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- NRL team news update"
& $uv run --with requests python scripts\update_team_news_injuries.py --sport NRL --season 2026
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -- Done."
