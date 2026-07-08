# run_afl_r15_thursday_reprice.ps1
# Fires at 2:10pm Thursday June 18 — after AFL squad announcements (2:00pm)
# Full reprice: injuries updated from squad drop, weather live, emotional flags, ML shadow

$ErrorActionPreference = "Stop"
$env:BETMATE_ROOT  = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8   = "1"

$ROOT    = "C:\Users\ElliotBladen\Apps\BettingEngine"
$PYTHON  = "$ROOT\.venv\Scripts\python.exe"
$LOGFILE = "$ROOT\logs\afl_r15_thursday_reprice.log"

New-Item -ItemType Directory -Force -Path "$ROOT\logs" | Out-Null

function Log { param($msg) $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; "$ts  $msg" | Tee-Object -FilePath $LOGFILE -Append }

Log "=== AFL R15 Thursday Reprice — POST SQUAD ANNOUNCEMENT ==="
Log "Squads dropped at 14:00 — running full T1-T7 + ML shadow"

# Step 0 — fresh emotional flags (Claude-powered, checks Google News + rivalry/milestone rules)
Log "Step 0: afl_emotional.py --round 15 (scrapes fresh flags before pricing)"
$UV = "C:\Users\ElliotBladen\.local\bin\uv.exe"
& $UV run --with anthropic --with openpyxl python "C:\Users\ElliotBladen\Apps\scrapers\afl_emotional.py" --round 15 2>&1 | Tee-Object -FilePath $LOGFILE -Append

# Step 1 — full reprice (injuries already in INJURIES[15] dict — update manually if needed)
Log "Step 1: prepare_afl_round.py --season 2026 --round 15"
& $PYTHON "$ROOT\scripts\prepare_afl_round.py" --season 2026 --round 15 2>&1 | Tee-Object -FilePath $LOGFILE -Append

# Step 2 — export to CSV
Log "Step 2: export prices to r15_afl_2026.csv"
& $PYTHON "$ROOT\scripts\_export_afl_prices.py" --season 2026 --round 15 2>&1 | Tee-Object -FilePath $LOGFILE -Append

# Step 3 — rerun matrix confluence (picks up any context changes) and push to Supabase
Log "Step 3: afl_matrix_confluence.py --round 15 --push"
& $PYTHON "$ROOT\scripts\afl_matrix_confluence.py" --season 2026 --round 15 --push 2>&1 | Tee-Object -FilePath $LOGFILE -Append

Log "=== Reprice complete. Check logs above for T5/T6/T7 output. ==="
Log "REMINDER: If squad drop reveals new outs, update INJURIES[15] in prepare_afl_round.py and re-run manually."
