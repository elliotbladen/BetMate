#!/usr/bin/env python3
"""Price EFL Championship 2026/27 GW8 (18-20 Sep) — 1X2.

Successor to scripts/price_efl_week7_normal_shadow_2026.py, which is the newest
Championship pricer in the repo (committed 2026-09-10 with three fault fixes).

WHAT IS DIFFERENT FROM GW7, AND IT MATTERS:
  The Championship 1X2 engine changed on 2026-09-15. `new_team_reset_1x2: elo_seeded`
  now seeds clubs new to the division from Elo instead of wiping them to league
  average. That was better in 10 of 10 walk-forward seasons (1.0366 vs a 1.0554
  baseline). Totals stay on `league_average` — the split is deliberate. GW7 and
  everything before it was priced on the OLD behaviour, so these prices are not
  comparable with that run.

  `matchweek` is passed per fixture as the games that club has ACTUALLY played,
  because T8's prior weight is a per-team decay, not a calendar week.

T6 referee is not injected — the EFL had not published GW8 appointments at build time.
T5 is not injected either; see the report for why that is a deliberate choice here.
"""
from __future__ import annotations
import contextlib, io, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.football.price_match import price_match  # noqa: E402

OUT = ROOT / "outputs" / "football" / "championship" / "2026-27" / "gw08"
SUP = OUT / "_supporting"

# Games played per club BEFORE GW8, from the results file (2026/27, 81 matches).
# Six clubs sit on 6 because three GW6 fixtures were postponed.
PLAYED = {t: 7 for t in [
    "Birmingham","Blackburn","Bolton","Burnley","Cardiff","Charlton","Derby","Norwich",
    "Preston","QPR","Sheffield United","Southampton","Stoke","Swansea","Watford",
    "West Brom","West Ham","Wrexham"]}
PLAYED.update({"Bristol City":6,"Lincoln":6,"Middlesbrough":6,"Millwall":6,
               "Portsmouth":6,"Wolves":6})

FIXTURES = [
    ("2026-09-18", "Bristol City",     "Watford"),
    ("2026-09-19", "Cardiff",          "Charlton"),
    ("2026-09-19", "Millwall",         "West Ham"),
    ("2026-09-19", "Stoke",            "Sheffield United"),
    ("2026-09-19", "Birmingham",       "Middlesbrough"),
    ("2026-09-19", "Portsmouth",       "Blackburn"),
    ("2026-09-19", "Burnley",          "Derby"),
    ("2026-09-19", "Lincoln",          "Swansea"),
    ("2026-09-19", "QPR",              "Preston"),
    ("2026-09-19", "Wrexham",          "Southampton"),
    ("2026-09-20", "Wolves",           "West Brom"),
    ("2026-09-20", "Norwich",          "Bolton"),
]
BOOK = 1.05

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); SUP.mkdir(exist_ok=True)
    games, working = [], []
    for date, home, away in FIXTURES:
        mw = min(PLAYED[home], PLAYED[away])
        s = io.StringIO()
        with contextlib.redirect_stdout(s):
            p = price_match(home, away, as_of=datetime.fromisoformat(date),
                            league="championship", matchweek=mw)
        if p is None:
            raise RuntimeError(f"engine did not price {home} v {away}")
        working.append(s.getvalue())
        ph, pd_, pa = p["p_home"], p["p_draw"], p["p_away"]
        t = ph + pd_ + pa; ph, pd_, pa = ph/t, pd_/t, pa/t
        games.append({"date": date, "home": home, "away": away, "matchweek": mw,
            "p_home": ph, "p_draw": pd_, "p_away": pa,
            "fair_home": round(1/ph,2), "fair_draw": round(1/pd_,2), "fair_away": round(1/pa,2),
            "price_home_105": round(1/(ph*BOOK),2), "price_draw_105": round(1/(pd_*BOOK),2),
            "price_away_105": round(1/(pa*BOOK),2),
            "lambda_home": p["lambda_home"], "lambda_away": p["lambda_away"],
            "new_team_resets": p.get("new_team_resets", []),
            "reset_mode_1x2": p.get("new_team_reset_mode_1x2"),
            "reset_mode_totals": p.get("new_team_reset_mode_totals")})
    payload = {"generated_at": datetime.now().isoformat(), "competition": "EFL Championship",
        "season": "2026/27", "matchweek": 8, "book": BOOK,
        "engine_note": "new_team_reset_1x2=elo_seeded (changed 2026-09-15); totals stay league_average",
        "limitations": [
            "T5 injuries NOT injected — see report; the documented Championship lesson is that "
            "most published absentees have already been absent for weeks and are in the ratings.",
            "T6 referee NOT injected — EFL had not published GW8 appointments.",
            "Bristol City, Lincoln, Middlesbrough and Millwall play a rearranged GW6 fixture on "
            "15 Sep whose result is NOT in this fit.",
        ], "games": games}
    (SUP/"gw08_prices.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (SUP/"gw08_full_working.txt").write_text("\n".join(working), encoding="utf-8")
    print(f"{'fixture':38s} {'mw':>3s} {'  H':>6s} {'  D':>6s} {'  A':>6s}  {'book':>6s}   {'P(H)':>6s} {'P(D)':>6s} {'P(A)':>6s}   {'xG':>10s}")
    for g in games:
        bk = 100*(1/g['price_home_105']+1/g['price_draw_105']+1/g['price_away_105'])
        print(f"{g['home']+' v '+g['away']:38s} {g['matchweek']:>3d} "
              f"{g['price_home_105']:6.2f} {g['price_draw_105']:6.2f} {g['price_away_105']:6.2f}  {bk:5.1f}%   "
              f"{g['p_home']*100:5.1f}% {g['p_draw']*100:5.1f}% {g['p_away']*100:5.1f}%   "
              f"{g['lambda_home']:4.2f}-{g['lambda_away']:4.2f}")

if __name__ == "__main__":
    main()
