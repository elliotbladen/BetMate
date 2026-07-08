import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREP = ROOT / "outputs" / "afl_round_prep" / "r11_2026"
PREP.mkdir(parents=True, exist_ok=True)

fixture = [
    ("Hawthorn Hawks",                "Adelaide Crows",     "MCG",              "2026-05-21"),
    ("Richmond Tigers",               "Essendon Bombers",   "MCG",              "2026-05-22"),
    ("Fremantle Dockers",             "St Kilda Saints",    "Optus Stadium",    "2026-05-22"),
    ("North Melbourne Kangaroos",     "Gold Coast Suns",    "Marvel Stadium",   "2026-05-23"),
    ("Geelong Cats",                  "Sydney Swans",       "GMHBA Stadium",    "2026-05-23"),
    ("Collingwood Magpies",           "West Coast Eagles",  "MCG",              "2026-05-23"),
    ("Port Adelaide Power",           "Carlton Blues",      "Adelaide Oval",    "2026-05-23"),
    ("Greater Western Sydney Giants", "Brisbane Lions",     "ENGIE Stadium",    "2026-05-24"),
    ("Western Bulldogs",              "Melbourne Demons",   "Marvel Stadium",   "2026-05-24"),
]

with open(PREP / "fixture_r11_2026.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["home_team", "away_team", "venue", "date"])
    w.writerows(fixture)
print(f"Wrote fixture: {len(fixture)} games")

inj_src = Path(r"C:\Users\ElliotBladen\Apps\data\afl\injuries\processed\latest-injuries.json")
raw = json.loads(inj_src.read_text(encoding="utf-8"))

team_map = {}
for rec in raw:
    if rec.get("status") != "out":
        continue
    team = rec["team"]
    if team not in team_map:
        team_map[team] = []
    team_map[team].append({
        "player":           rec["player"],
        "position":         "utility",
        "quality":          "average",
        "status":           "out",
        "injury":           rec.get("notes", ""),
        "estimated_return": "",
    })

payload = {"injuries": team_map}
(PREP / "injuries_r11_2026.json").write_text(
    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
)
total = sum(len(v) for v in team_map.values())
print(f"Wrote injuries: {total} outs across {len(team_map)} teams")
print("Done.")
