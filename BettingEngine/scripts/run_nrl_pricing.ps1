$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8 = "1"

& "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
    "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\prepare_round.py" `
    --season 2026 --round 0
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Export pricing CSV (round auto-detected from DB via same logic)
$roundNum = & "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" -c @"
import sys, json
from pathlib import Path
fixture = Path(r'C:\Users\ElliotBladen\Apps\data\nrl\fixture\processed\latest-fixture.json')
data = json.loads(fixture.read_text())
print(data['round'])
"@
if ($LASTEXITCODE -eq 0 -and $roundNum) {
    & "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
        "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\export_round_csv.py" `
        --season 2026 --round $roundNum
}

# Push matrices to Supabase so Vercel can serve EV signals
& "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
    "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\push_matrices_to_supabase.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Baz reads the sanitised Supabase context, not the local pricing CSV. A round
# is therefore not released until its current context has been published.
& "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
    "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\publish_current_baz_context.py" NRL
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

exit 0
