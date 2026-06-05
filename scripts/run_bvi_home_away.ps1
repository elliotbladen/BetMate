# run_bvi_home_away.ps1
#
# Shared wrapper for all BVI + Home/Away scrapers.
# Loads Supabase env vars from .env.local, then runs the scraper passed as $args[0].
# Called by Task Scheduler for AFL BVI, AFL H/A, NRL BVI, NRL H/A.
#
# Usage: powershell.exe -File run_bvi_home_away.ps1 <scraper_path>

param([string]$ScraperPath)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\ElliotBladen\Apps"
$uvExe    = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$envFile  = Join-Path $repoRoot ".env.local"

# Load Supabase keys from .env.local
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            $key   = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

$env:PYTHONUTF8 = "1"

# Resolve certifi CA bundle so requests can verify SSL on Windows
$certPath = & $uvExe run --with certifi python -c "import certifi; print(certifi.where())" 2>$null
if ($certPath) { $env:REQUESTS_CA_BUNDLE = $certPath.Trim() }

& $uvExe run --with requests --with beautifulsoup4 --with certifi python $ScraperPath
exit $LASTEXITCODE
