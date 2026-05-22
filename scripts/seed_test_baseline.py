"""Seed today's latest.csv as the opening baseline for testing."""
# /// script
# dependencies = ["requests"]
# ///
import csv, json, os
from datetime import datetime
from pathlib import Path

import requests

ROOT     = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.local"

for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

url = os.environ["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/")
svc = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

latest = ROOT / "data" / "odds_snapshots" / "latest.csv"
with latest.open(newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

def side_for(row):
    o, h, a = row.get("outcome",""), row.get("home_team",""), row.get("away_team","")
    if o == h:             return "home"
    if o == a:             return "away"
    if o.lower() == "over":  return "over"
    if o.lower() == "under": return "under"
    return None

for sport in ("NRL", "AFL"):
    prices = {}
    for row in rows:
        if row["sport"] != sport: continue
        s = side_for(row)
        if not s: continue
        k = f"{row['game_id']}:{row['market']}:{row['bookmaker']}:{s}"
        prices[k] = {
            "price":        float(row["price"]),
            "home_team":    row["home_team"],
            "away_team":    row["away_team"],
            "commence_time":row["commence_time"],
        }
    payload = [{"key": f"{sport.lower()}_opening_baseline", "data": {
        "captured_at": datetime.now().isoformat(),
        "sport": sport,
        "prices": prices,
    }}]
    resp = requests.post(
        f"{url}/rest/v1/betmate_data_store",
        headers={"apikey": svc, "Authorization": f"Bearer {svc}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"},
        data=json.dumps(payload), timeout=10,
    )
    resp.raise_for_status()
    print(f"{sport} baseline seeded — {len(prices)} prices")
