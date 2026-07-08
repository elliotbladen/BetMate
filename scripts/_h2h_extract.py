import os, glob, csv
from collections import defaultdict

SNAP_DIR = r"C:\Users\ElliotBladen\Apps\data\odds_snapshots\2026"
files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))

# First pass: collect earliest TAB H2H odds per game_id per team
game_odds = {}  # game_id -> {home, away, home_odds, away_odds, sport, date}

for fpath in files:
    snap_date = os.path.basename(fpath).replace(".csv", "")
    with open(fpath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("market") != "h2h":
                continue
            if row.get("bookmaker") != "tab":
                continue
            sport = row.get("sport", "")
            if sport not in ("NRL", "AFL"):
                continue
            gid = row["game_id"]
            if gid not in game_odds:
                game_odds[gid] = {
                    "sport": sport,
                    "snap_date": snap_date,
                    "home": row["home_team"],
                    "away": row["away_team"],
                    "commence": row["commence_time"][:10],
                    "home_odds": None,
                    "away_odds": None
                }
            team = row["outcome"]
            price = float(row["price"]) if row["price"] else None
            if team == row["home_team"]:
                if game_odds[gid]["home_odds"] is None:
                    game_odds[gid]["home_odds"] = price
            elif team == row["away_team"]:
                if game_odds[gid]["away_odds"] is None:
                    game_odds[gid]["away_odds"] = price

# Print all unique games with their earliest TAB odds
print("sport|snap_date|commence|home|away|home_odds|away_odds")
for gid, g in sorted(game_odds.items(), key=lambda x: x[1]["commence"]):
    print(f"{g['sport']}|{g['snap_date']}|{g['commence']}|{g['home']}|{g['away']}|{g['home_odds']}|{g['away_odds']}")
