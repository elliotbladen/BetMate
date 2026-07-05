import argparse, csv, sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--season', type=int, default=2026)
parser.add_argument('--round',  type=int, default=13)
args = parser.parse_args()

ROOT = Path(__file__).resolve().parent.parent
DB   = ROOT / "data" / "model.db"
OUT  = ROOT / "results" / f"r{args.round:02d}_afl_{args.season}.csv"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT * FROM afl_shadow_predictions
    WHERE season=? AND round_number=?
    ORDER BY game_date, home_team
""", (args.season, args.round)).fetchall()

if not rows:
    print(f"No rows found in afl_shadow_predictions for R{args.round} {args.season}")
    raise SystemExit(1)

fields = list(rows[0].keys())
OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows([dict(r) for r in rows])

print(f"Written {len(rows)} rows to {OUT.name}")
print()

print(f"  {'Matchup':<42} {'H2H Home':>9} {'H2H Away':>9}  {'Handicap':<22} {'Total':>7}")
print("  " + "-" * 95)
for r in rows:
    home_last = r['home_team'].split()[-1]
    away_last = r['away_team'].split()[-1]
    matchup = f"{home_last} vs {away_last}"
    margin = r['rules_margin']
    hcap_line = abs(margin)
    if margin > 0:
        hcap = f"{home_last} -{hcap_line:.1f}"
    else:
        hcap = f"{away_last} -{hcap_line:.1f}"
    print(f"  {matchup:<42} {r['rules_home_odds']:>9.2f} {r['rules_away_odds']:>9.2f}  {hcap:<22} {r['rules_total']:>7.1f}")

conn.close()
