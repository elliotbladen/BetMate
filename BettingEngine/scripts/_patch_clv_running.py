"""
Patch actual_bets_clv_2026.csv with R13 NRL + R12 AFL CLV data,
then run update_clv_running to rebuild the running totals.
"""
import csv, subprocess, sys
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
MASTER   = ROOT / "data" / "clv" / "running" / "actual_bets_clv_2026.csv"
WEEKEND  = ROOT / "data" / "clv" / "nrl" / "NRL_AFL_BETS_CLV_R13_R12_2026-06-03.csv"
BETS     = ROOT / "data" / "bets" / "actual_bets_2026.csv"

# ── load master CLV (existing) ─────────────────────────────────────────────────
with open(MASTER, encoding="utf-8-sig") as f:
    master_rows = list(csv.DictReader(f))
    master_ids  = {r["bet_id"] for r in master_rows}

master_fields = list(master_rows[0].keys()) if master_rows else [
    "bet_id","sport","round","match","market","selection",
    "line","odds_taken","open_line","close_line","line_move",
    "close_odds","clv_pct","clv_line","pnl","result"
]

# ── load weekend CLV ───────────────────────────────────────────────────────────
with open(WEEKEND, encoding="utf-8") as f:
    weekend_rows = list(csv.DictReader(f))
print(f"Weekend CLV rows: {len(weekend_rows)}")

# ── load bets for week_ending / pnl / round ────────────────────────────────────
bets_meta = {}
with open(BETS, encoding="utf-8-sig") as f:
    for b in csv.DictReader(f):
        bets_meta[b["bet_id"]] = b

# ── build new rows for R13 NRL + R12 AFL ──────────────────────────────────────
new_rows = []
skipped  = []

for w in weekend_rows:
    bid = w["bet_id"]
    if bid in master_ids:
        print(f"  Already in master: {bid}")
        continue

    clv = w.get("clv_pct","")
    if clv in ("", "None", None):
        clv = ""

    b = bets_meta.get(bid, {})
    home = w.get("home","")
    away = w.get("away","")
    match_str = f"{home.split()[-1]} v {away.split()[-1]}"

    # line_move: open_line -> close_line
    ol = w.get("open_line","")
    cl = w.get("close_line","")
    lm = ""
    try:
        lm = str(round(float(cl) - float(ol), 1)) if ol and cl else ""
    except: pass

    pnl = b.get("pnl","") or ""
    if not pnl:
        # estimate from stake + result
        try:
            stake = float(b.get("stake","25") or 25)
            odds  = float(w.get("odds_taken","") or 0)
            result = (w.get("result","") or "").upper()
            if result == "WIN":
                pnl = str(round(stake * odds - stake, 2))
            elif result == "LOSS":
                pnl = str(round(-stake, 2))
        except: pass

    row = {
        "bet_id":    bid,
        "sport":     w.get("sport",""),
        "round":     b.get("round",""),
        "match":     match_str,
        "market":    w.get("market",""),
        "selection": w.get("selection",""),
        "line":      w.get("line",""),
        "odds_taken":w.get("odds_taken",""),
        "open_line": ol,
        "close_line":cl,
        "line_move": lm,
        "close_odds":w.get("close_odds",""),
        "clv_pct":   clv,
        "clv_line":  "",
        "pnl":       pnl,
        "result":    w.get("result",""),
    }
    new_rows.append(row)

print(f"New rows to append: {len(new_rows)}")
for r in new_rows:
    clv_str = f"{float(r['clv_pct']):+.2f}%" if r['clv_pct'] else "n/a"
    print(f"  {r['bet_id']}  {r['sport']} R{r['round']}  {r['match']}  {r['market']}  CLV:{clv_str}  {r['result']}")

# ── append to master ───────────────────────────────────────────────────────────
all_rows = master_rows + new_rows
with open(MASTER, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=master_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(all_rows)
print(f"\nMaster updated: {len(all_rows)} total rows ({len(new_rows)} added)")

# ── run update_clv_running ─────────────────────────────────────────────────────
print("\nRunning update_clv_running.py...")
result = subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "update_clv_running.py")],
    cwd=str(ROOT), capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print("ERRORS:", result.stderr[-500:])
