param(
    [int]$Round  = 13,
    [int]$Season = 2026
)

$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8  = "1"

$py   = "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe"
$root = "C:\Users\ElliotBladen\Apps\BettingEngine"
$xlsx = "$root\outputs\afl_weekly_review\historical\latest.xlsx"

# Step 1 — Rebuild ELO from latest historical xlsx
if (Test-Path $xlsx) {
    Write-Host "[AFL Pricing R$Round] Step 1: Rebuilding ELO from $xlsx ..."
    & $py "$root\ml\afl\game_log.py" --xlsx $xlsx
    if ($LASTEXITCODE -ne 0) { Write-Error "ELO rebuild failed"; exit $LASTEXITCODE }
} else {
    Write-Warning "latest.xlsx not found — pricing will use stale ELO"
}

# Step 2 — Run T1-T6 pricing + ML shadow
Write-Host "[AFL Pricing R$Round] Step 2: prepare_afl_round.py --season $Season --round $Round"
& $py "$root\scripts\prepare_afl_round.py" --season $Season --round $Round
if ($LASTEXITCODE -ne 0) { Write-Error "prepare_afl_round.py failed"; exit $LASTEXITCODE }

# Step 3 — Export pricing CSV
Write-Host "[AFL Pricing R$Round] Step 3: _export_afl_prices.py --season $Season --round $Round"
& $py "$root\scripts\_export_afl_prices.py" --season $Season --round $Round
if ($LASTEXITCODE -ne 0) { Write-Error "_export_afl_prices.py failed"; exit $LASTEXITCODE }

Write-Host "[AFL Pricing R$Round] Done. Output: $root\results\r$($Round.ToString('D2'))_afl_$Season.csv"
exit 0
