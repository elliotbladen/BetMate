# run_nrl_referees.ps1 — wrapper for Task Scheduler
# Scrapes NRL referee appointments and writes latest-referees.csv

param(
    [string]$UvExe  = "C:\Users\ElliotBladen\.local\bin\uv.exe",
    [int]$Season    = 2026
)

$WorkDir = "C:\Users\ElliotBladen\Apps"
$LogDir  = "$WorkDir\data\nrl\referees\logs"
$LogFile = "$LogDir\task.log"

New-Item -ItemType Directory -Force $LogDir | Out-Null

Set-Location $WorkDir
& $UvExe run --with requests --with beautifulsoup4 python lib\scraper\nrl_referees.py --season $Season >> $LogFile 2>&1
