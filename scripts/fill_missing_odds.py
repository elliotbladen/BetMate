"""
fill_missing_odds.py  (v2)

Fills in null odds in LEGACY_BETS:
  WIN  — odds = cumPL[i] - cumPL[prev consecutive id] + 1
  LOSS — cannot be derived (always -1 unit); default 1.9
  PUSH — set 1.9 (P&L is 0 regardless)
"""

import re
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[1]
TS_FILE = ROOT / "lib" / "researchData.ts"

content = TS_FILE.read_text(encoding="utf-8")

# Robust line regex: allows optional spaces after colons, handles cumPL sign
LINE_RE = re.compile(
    r'\{ id:(\d+),.*?odds:(null|[\d.]+),.*?result:\'(win|loss|push)\','
    r'.*?cumPL:\s*([-\d.]+)',
    re.DOTALL
)

# Parse bets but restrict to lines (don't let DOTALL cross more than one entry)
# Parse line by line instead
bets = []
for line in content.splitlines():
    m = re.search(
        r'\{ id:(\d+),.*?odds:(null|[\d.]+),.*?result:\'(win|loss|push)\','
        r'.*?cumPL:\s*([-\d.]+)',
        line
    )
    if m:
        bets.append({
            "id":      int(m.group(1)),
            "odds":    None if m.group(2) == "null" else float(m.group(2)),
            "result":  m.group(3),
            "cumPL":   float(m.group(4)),
        })

print(f"Parsed {len(bets)} bets")

bets_sorted = sorted(bets, key=lambda b: b["id"])

# Compute fixes
fixes: dict[int, float] = {}
for i, bet in enumerate(bets_sorted):
    if bet["odds"] is not None:
        continue

    if bet["result"] in ("loss", "push"):
        fixes[bet["id"]] = 1.9
        continue

    # WIN: try cumPL diff from previous consecutive id
    if i > 0:
        prev = bets_sorted[i - 1]
        if prev["id"] == bet["id"] - 1:
            diff = round(bet["cumPL"] - prev["cumPL"], 4)
            if 0.05 < diff < 20:
                fixes[bet["id"]] = round(diff + 1, 2)
            else:
                fixes[bet["id"]] = 1.9
        else:
            fixes[bet["id"]] = 1.9
    else:
        fixes[bet["id"]] = 1.9

print(f"\n{len(fixes)} null-odds entries to fill:")
print(f"{'ID':>5}  {'Result':<6}  {'Odds':>6}")
print("-" * 25)
for bid, odds in sorted(fixes.items()):
    bet = next(b for b in bets_sorted if b["id"] == bid)
    print(f"{bid:>5}  {bet['result']:<6}  {odds:>6.2f}")

# Apply fixes — replace `odds:null` on the specific line for each bet id
new_content = content
missed = []
for bet_id, new_odds in sorted(fixes.items()):
    # Match the exact line containing this bet's id
    pattern = re.compile(
        rf"({{ id:{bet_id},)(.*?)(odds:null)(.*?}})"
    )
    replacement = rf"\g<1>\g<2>odds:{new_odds}\g<4>"
    updated, n = pattern.subn(replacement, new_content, count=1)
    if n == 0:
        missed.append(bet_id)
    else:
        new_content = updated

# Check remaining nulls
still_null = re.findall(r"id:(\d+),.*?odds:null", new_content)
print(f"\nStill null after fix: {len(still_null)}")
if still_null:
    print("  IDs:", still_null)
if missed:
    print(f"  Could not replace: {missed}")

TS_FILE.write_text(new_content, encoding="utf-8")
print(f"\nDone. Wrote {TS_FILE}")
