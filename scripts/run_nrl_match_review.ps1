# run_nrl_match_review.ps1
# Wrapper for "BetMate NRL Match Review" Task Scheduler task.
# Loads env, runs nrl_match_review.py via uv.

$ErrorActionPreference = "Stop"
$repoRoot = "C:\Users\ElliotBladen\Apps"
$uvExe    = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$envFile  = Join-Path $repoRoot ".env.local"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$env:PYTHONUTF8 = "1"

& $uvExe run --with requests --with beautifulsoup4 python "$repoRoot\scrapers\nrl_match_review.py"
exit $LASTEXITCODE
