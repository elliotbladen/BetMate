# run_nrl_emotional.ps1 — wrapper for Task Scheduler
# Loads .env.local so ANTHROPIC_API_KEY is available, then runs the emotional scraper.

$EnvFile  = "C:\Users\ElliotBladen\Apps\BetMate\.env.local"
$UvPath   = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$Script   = "C:\Users\ElliotBladen\Apps\lib\scraper\nrl_emotional.py"
$WorkDir  = "C:\Users\ElliotBladen\Apps"
$LogDir   = "C:\Users\ElliotBladen\Apps\data\nrl\emotional\logs"
$LogFile  = "$LogDir\task.log"

New-Item -ItemType Directory -Force $LogDir | Out-Null

# Load .env.local
Get-Content $EnvFile | Where-Object { $_ -match "^[A-Z_]+=.+" } | ForEach-Object {
    $key, $val = $_ -split "=", 2
    [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
}

Set-Location $WorkDir
& $UvPath run --with anthropic --with requests python $Script --round 0 >> $LogFile 2>&1
