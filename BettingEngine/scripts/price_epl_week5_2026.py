#!/usr/bin/env python3
"""Price EPL 2026/27 GW5 (18-20 Sep) with the production engine — 1X2 and O/U 2.5.

Follows scripts/price_epl_week3_normal_shadow_2026.py but drops the player shadow:
that model needs current ESPN starting-XI feeds, which are not refreshed for GW5, and
a shadow built on stale XIs is worse than no shadow.

T5 IS PARTIAL AND SAYS SO. Only six clubs could be audited from a source that actually
serves its data (Fantasy Football Scout, 14 Sep). premierleague.com/latest-player-injuries
and rotowire are both JS-rendered or paywalled to WebFetch. Clubs with no entry below are
NOT injury-free — they are unaudited, and every one of them is flagged in the report.
"""
from __future__ import annotations
import contextlib, io, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.football.price_match import price_match  # noqa: E402
OUT = ROOT / "outputs" / "football" / "epl" / "2026-27" / "gw05"
SUP = OUT / "_supporting"

FIXTURES = [
    ("2026-09-18", "Brentford",     "Chelsea"),
    ("2026-09-19", "Tottenham",     "Aston Villa"),
    ("2026-09-19", "Brighton",      "Arsenal"),
    ("2026-09-19", "Everton",       "Ipswich"),
    ("2026-09-19", "Newcastle",     "Hull"),
    ("2026-09-19", "Nott'm Forest", "Coventry"),
    ("2026-09-20", "Bournemouth",   "Liverpool"),
    ("2026-09-20", "Leeds",         "Crystal Palace"),
    ("2026-09-20", "Man City",      "Sunderland"),
    ("2026-09-20", "Fulham",        "Man United"),
]

# Confirmed absences only. Doubts excluded until confirmed (engine convention).
ABSENCES = {
    "Liverpool":  [("Hugo Ekitike","ST"),("Conor Bradley","RB"),("Giovanni Leoni","CB"),
                   ("Federico Chiesa","FW")],
    "Tottenham":  [("Mykhailo Mudryk","LW"),("Xavi Simons","AM"),("Wilson Odobert","LW"),
                   ("Dejan Kulusevski","AM"),("Pedro Porro","RB"),("Sandro Tonali","CM")],
    "Brentford":  [("Kaye Furo","CM"),("Nathan Collins","CB"),("Mathias Jensen","CM"),
                   ("Sepp van den Berg","CB"),("Josh Dasilva","CM"),("Antoni Milambo","CM")],
    "Fulham":     [("Tom Cairney","CM"),("Ryan Sessegnon","LB")],
    "Ipswich":    [("Jack Taylor","CM")],
    "Man City":   [("Jeremy Doku","LW")],
    "Aston Villa":[("Joao Gomes","CM")],          # suspended — violent conduct red
}
DOUBTS = {"Ipswich": ["Emersonn (ST, won't be risked midweek)"],
          "Liverpool": ["Joe Gomez (muscle) — back in training, available"]}
UNAUDITED = ["Arsenal","Brighton","Chelsea","Coventry","Crystal Palace","Everton",
             "Hull","Leeds","Man United","Newcastle","Nott'm Forest","Sunderland"]

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); SUP.mkdir(exist_ok=True)
    games, working = [], []
    for date, home, away in FIXTURES:
        s = io.StringIO()
        with contextlib.redirect_stdout(s):
            p = price_match(home, away, as_of=datetime.fromisoformat(date), league="epl",
                            matchweek=5,
                            injuries_home=[pos for _, pos in ABSENCES.get(home, [])],
                            injuries_away=[pos for _, pos in ABSENCES.get(away, [])])
        if p is None:
            raise RuntimeError(f"engine did not price {home} v {away}")
        working.append(s.getvalue())
        games.append({"date": date, "home": home, "away": away,
                      "absences_home": ABSENCES.get(home, []), "absences_away": ABSENCES.get(away, []),
                      "home_unaudited": home in UNAUDITED, "away_unaudited": away in UNAUDITED,
                      "price": p})
    payload = {"generated_at": datetime.now().isoformat(), "competition": "EPL",
               "season": "2026/27", "matchweek": 5,
               "limitations": [
                 "T5 PARTIAL: only 6 clubs audited from a source that serves its data; "
                 "12 clubs are UNAUDITED, not injury-free.",
                 "No player shadow — ESPN starting-XI feeds are not refreshed for GW5.",
                 "No referee appointments injected (T6 = 0).",
                 "No market odds injected — EV is not computed here.",
               ], "games": games}
    (SUP / "gw05_prices.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (SUP / "gw05_full_working.txt").write_text("\n".join(working), encoding="utf-8")
    print(f"{'fixture':38s} {'1X2 fair (H/D/A)':>26s} {'P(H)':>7s} {'P(D)':>7s} {'P(A)':>7s} {'xG':>11s} {'O2.5':>7s} {'fair O':>7s} {'fair U':>7s}")
    for g in games:
        p = g["price"]
        print(f"{g['home']+' v '+g['away']:38s} "
              f"{p['fair_home']:7.2f} {p['fair_draw']:7.2f} {p['fair_away']:7.2f}  "
              f"{p['p_home']*100:6.1f}% {p['p_draw']*100:6.1f}% {p['p_away']*100:6.1f}% "
              f"{p['lambda_home']:5.2f}-{p['lambda_away']:4.2f} "
              f"{p['p_over25']*100:6.1f}% {p['fair_over25']:7.2f} {p['fair_under25']:7.2f}")

if __name__ == "__main__":
    main()
