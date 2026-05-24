# run_afl_emotional.ps1 — wrapper for Task Scheduler
# Loads .env.local for ANTHROPIC_API_KEY, then runs the AFL emotional scraper.

$EnvFile = "C:\Users\ElliotBladen\Apps\.env.local"
$UvPath  = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$Script  = "C:\Users\ElliotBladen\Apps\scrapers\afl_emotional.py"
$WorkDir = "C:\Users\ElliotBladen\Apps"
$LogDir  = "C:\Users\ElliotBladen\Apps\data\afl\emotional\logs"
$LogFile = "$LogDir\task.log"

New-Item -ItemType Directory -Force $LogDir | Out-Null

Get-Content $EnvFile | Where-Object { $_ -match "^[A-Z_]+=.+" } | ForEach-Object {
    $key, $val = $_ -split "=", 2
    [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
}

$env:PYTHONUTF8 = "1"
Set-Location $WorkDir
& $UvPath run --with anthropic python $Script --round 0 >> $LogFile 2>&1
