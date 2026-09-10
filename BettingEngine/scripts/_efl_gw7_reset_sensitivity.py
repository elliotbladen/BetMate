#!/usr/bin/env python3
"""How much of GW7's model edge is an artefact of the new-team D-C reset?

`_reset_new_team_dc_ratings` forces every club that was not in the division last
season to att=1.00 / def=1.00 / hfa=1.00, which also discards the 5-6 games they
have played this season. Six of the 24 Championship clubs are affected
(Burnley, West Ham, Wolves down; Bolton, Cardiff, Lincoln up), and they appear
in 5 of the 12 GW7 fixtures.

This re-prices those fixtures with the reset replaced by a current-season
estimate: D-C fitted on 2026/27 results only, shrunk toward league average by
n/(n+6) to respect the small sample. It is an indicative band, not a production
price -- the point is the direction and size of the distortion, not a new number
to bet.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ml.football.price_match as pm  # noqa: E402
from ml.football.models.dixon_coles import fit as dc_fit  # noqa: E402

OUT = ROOT / "outputs" / "football" / "championship" / "2026-27" / "gw07" / "_supporting"
MARKET = json.loads((Path(__file__).resolve().parent / "_efl_gw7_market_2026.json").read_text())
ABSENCES = json.loads((Path(__file__).resolve().parent / "_efl_gw7_absences_2026.json").read_text())
GAMES_PLAYED = {
    "Birmingham": 6, "Blackburn": 6, "Bolton": 6, "Bristol City": 5, "Burnley": 6,
    "Cardiff": 6, "Charlton": 6, "Derby": 6, "Lincoln": 5, "Middlesbrough": 5,
    "Millwall": 5, "Norwich": 6, "Portsmouth": 5, "Preston": 6, "QPR": 6,
    "Sheffield United": 6, "Southampton": 6, "Stoke": 6, "Swansea": 6,
    "Watford": 6, "West Brom": 6, "West Ham": 6, "Wolves": 5, "Wrexham": 6,
}
AFFECTED = [
    ("2026-09-11", "West Ham", "Wrexham"),
    ("2026-09-12", "Bolton", "Cardiff"),
    ("2026-09-12", "Preston", "Lincoln"),
    ("2026-09-12", "Swansea", "Burnley"),
    ("2026-09-13", "Sheffield United", "Wolves"),
]
SHRINK_PRIOR_GAMES = 6.0

_original_reset = pm._reset_new_team_dc_ratings
_current_season_cache: dict | None = None


def current_season_ratings(df: pd.DataFrame, as_of: datetime) -> dict:
    global _current_season_cache
    if _current_season_cache is None:
        season = df[df["Season"] == "2026/27"].rename(
            columns={"HomeTeam": "home_team", "AwayTeam": "away_team"})
        with contextlib.redirect_stdout(io.StringIO()):
            _current_season_cache = dc_fit(season, as_of=as_of, rho=-0.13, decay_rate=0.0)
    return _current_season_cache


def patched_reset(ratings, df, teams, as_of):
    """Replace the flat league-average reset with a shrunk current-season fit."""
    ratings = _original_reset(ratings, df, teams, as_of)
    reset = ratings.get("new_team_resets") or []
    if not reset:
        return ratings
    cur = current_season_ratings(df, as_of)
    ratings = {**ratings, "attack": dict(ratings["attack"]),
               "defence": dict(ratings["defence"]), "reset_override": {}}
    for team in reset:
        n = float(GAMES_PLAYED.get(team, 5))
        w = n / (n + SHRINK_PRIOR_GAMES)
        att = 1.0 + w * (float(cur["attack"].get(team, 1.0)) - 1.0)
        dfc = 1.0 + w * (float(cur["defence"].get(team, 1.0)) - 1.0)
        ratings["attack"][team] = att
        ratings["defence"][team] = dfc
        ratings["reset_override"][team] = {"att": att, "def": dfc, "weight": w,
                                           "raw_att": float(cur["attack"].get(team, 1.0)),
                                           "raw_def": float(cur["defence"].get(team, 1.0))}
    return ratings


def price(date, home, away, patched: bool):
    pm._reset_new_team_dc_ratings = patched_reset if patched else _original_reset
    mkt = MARKET[f"{home} v {away}"]
    with contextlib.redirect_stdout(io.StringIO()):
        return pm.price_match(
            home, away, as_of=datetime.fromisoformat(date), league="championship",
            matchweek=GAMES_PLAYED[home],
            injuries_home=[p for _, p in ABSENCES.get(home, [])],
            injuries_away=[p for _, p in ABSENCES.get(away, [])],
            mkt_home=mkt["avg_home"], mkt_draw=mkt["avg_draw"],
            mkt_away=mkt["avg_away"], mkt_over25=mkt["avg_over25"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for date, home, away in AFFECTED:
        base = price(date, home, away, patched=False)
        alt = price(date, home, away, patched=True)
        rows.append({"date": date, "home": home, "away": away,
                     "production": {k: base[k] for k in
                                    ("p_home", "p_draw", "p_away", "p_over25",
                                     "lambda_home", "lambda_away")},
                     "current_season_ratings": {k: alt[k] for k in
                                                ("p_home", "p_draw", "p_away", "p_over25",
                                                 "lambda_home", "lambda_away")}})
    over = current_season_ratings(
        pd.read_csv(ROOT / "ml/football/data/championship/matches/championship_matches.csv",
                    parse_dates=["Date"], low_memory=False),
        datetime.fromisoformat("2026-09-13"))
    payload = {"generated_at": datetime.now().isoformat(),
               "method": "D-C refit on 2026/27 results only, shrunk to league average by n/(n+6)",
               "shrink_prior_games": SHRINK_PRIOR_GAMES,
               "current_season_attack": {t: round(float(over["attack"][t]), 4)
                                         for t in sorted(over["attack"])},
               "current_season_defence": {t: round(float(over["defence"][t]), 4)
                                          for t in sorted(over["defence"])},
               "fixtures": rows}
    (OUT / "reset_sensitivity.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"{'fixture':<34}{'prod H/D/A':<26}{'current-season H/D/A':<26} dP(home)")
    print("-" * 100)
    for r in rows:
        p, a = r["production"], r["current_season_ratings"]
        print(f"{r['home']+' v '+r['away']:<34}"
              f"{p['p_home']:.3f}/{p['p_draw']:.3f}/{p['p_away']:.3f}      "
              f"{a['p_home']:.3f}/{a['p_draw']:.3f}/{a['p_away']:.3f}      "
              f"{a['p_home']-p['p_home']:+.3f}")
    print(f"\nwrote {OUT / 'reset_sensitivity.json'}")


if __name__ == "__main__":
    main()
