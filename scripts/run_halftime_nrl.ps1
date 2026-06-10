# run_halftime_nrl.ps1
# Full NRL half-time pipeline: collect stats → price → anomaly matrix
#
# Usage:
#   # Manual entry for a specific game:
#   .\scripts\run_halftime_nrl.ps1 -Round 14 -Home "Cronulla-Sutherland Sharks" -Away "Manly-Warringah Sea Eagles"
#
#   # Auto-detect half-time games in the round:
#   .\scripts\run_halftime_nrl.ps1 -Round 14 -Auto
#
#   # Run just the matrix on already-collected stats:
#   .\scripts\run_halftime_nrl.ps1 -Round 14 -MatrixOnly

param(
    [int]    $Round   = 0,
    [string] $Home    = "",
    [string] $Away    = "",
    [switch] $Auto,
    [switch] $MatrixOnly,
    [switch] $Push
)

$ErrorActionPreference = "Stop"
$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8   = "1"
$UV   = "C:\Users\ElliotBladen\.local\bin\uv.exe"
$ROOT = "C:\Users\ElliotBladen\Apps"
$BE   = "$ROOT\BettingEngine"

if ($Round -eq 0) {
    Write-Host "ERROR: --Round is required." -ForegroundColor Red
    exit 1
}

# ── Step 1: Collect half-time stats ───────────────────────────────────────────
if (-not $MatrixOnly) {
    Write-Host "`n[1/3] Collecting half-time stats (R$Round)..." -ForegroundColor Cyan

    if ($Auto) {
        & $UV run python "$ROOT\scrapers\nrl_halftime_stats.py" `
            --round $Round --auto
    } elseif ($Home -and $Away) {
        & $UV run python "$ROOT\scrapers\nrl_halftime_stats.py" `
            --round $Round --manual --home $Home --away $Away
    } else {
        Write-Host "ERROR: Provide -Home and -Away for manual mode, or use -Auto." -ForegroundColor Red
        exit 1
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Stats collection failed." -ForegroundColor Red
        exit 1
    }
}

# ── Step 2: Price the half-time state ─────────────────────────────────────────
Write-Host "`n[2/3] Running half-time pricing model..." -ForegroundColor Cyan

$priceArgs = @("run", "python", "$BE\scripts\halfTime_price_nrl.py",
               "--round", $Round, "--save")
if ($Home -and $Away) {
    $priceArgs += @("--home", $Home, "--away", $Away)
}

& $UV @priceArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Pricing model failed." -ForegroundColor Yellow
    # Non-fatal — continue to matrix
}

# ── Step 3: Anomaly matrix ────────────────────────────────────────────────────
Write-Host "`n[3/3] Running anomaly matrix..." -ForegroundColor Cyan

$matrixArgs = @("run", "python", "$BE\scripts\halfTime_matrix_nrl.py",
                "--round", $Round, "--save")
if ($Push) {
    $matrixArgs += "--push"
}

& $UV @matrixArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Matrix failed." -ForegroundColor Red
    exit 1
}

Write-Host "`nHalf-time pipeline complete." -ForegroundColor Green
Write-Host "Matrix output: $BE\outputs\nrl_halftime_matrix_latest.json"
