"""Verify the per-market split composes exactly from the two measured arms.

Championship prices 1X2 off `elo_seeded` ratings and totals off `league_average`.
This asserts that composition is exact — the split's 1X2 must equal a whole-model
elo_seeded run and its totals a whole-model league_average run — which is what
lets the measured backtest numbers (1X2 1.0366, 10/10 seasons; O/U 0.6908
unchanged) be claimed for the split without re-running the 10-season walk-forward.

Exits non-zero on mismatch, so it can gate a change to price_match.

Usage:  python scripts/verify_new_team_reset_split.py
"""
import contextlib, io, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ml.football.price_match as pm
from ml.football.league_config import load_league

BASE = load_league("championship")

def run(mode_totals, mode_1x2, home, away, when):
    cfg = load_league("championship")
    cfg.model["new_team_reset"] = mode_totals
    cfg.model["new_team_reset_1x2"] = mode_1x2
    orig = pm.load_league
    pm.load_league = lambda lg: cfg
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return pm.price_match(home, away, as_of=when, league="championship")
    finally:
        pm.load_league = orig

FIXTURES = [("West Ham", "Wrexham", datetime(2026, 9, 11)),
            ("Bolton", "Cardiff", datetime(2026, 9, 12)),
            ("Sheffield United", "Wolves", datetime(2026, 9, 13))]

ok = True
for home, away, when in FIXTURES:
    avg   = run("league_average", "league_average", home, away, when)
    elo   = run("elo_seeded",     "elo_seeded",     home, away, when)
    split = run("league_average", "elo_seeded",     home, away, when)
    if not all((avg, elo, split)):
        print(f"SKIP {home} v {away}: no price"); continue

    x_ok = all(abs(split[k] - elo[k]) < 1e-9 for k in ("p_home", "p_draw", "p_away"))
    t_ok = all(abs(split[k] - avg[k]) < 1e-9 for k in ("p_over25", "p_under25"))
    differs = abs(elo["p_home"] - avg["p_home"]) > 1e-6

    print(f"\n{home} v {away}")
    print(f"  p_home   avg {avg['p_home']:.6f}  elo {elo['p_home']:.6f}  split {split['p_home']:.6f}"
          f"   -> 1X2 == elo_seeded: {x_ok}")
    print(f"  p_over25 avg {avg['p_over25']:.6f}  elo {elo['p_over25']:.6f}  split {split['p_over25']:.6f}"
          f"   -> totals == league_average: {t_ok}")
    print(f"  modes reported: 1X2={split['new_team_reset_mode_1x2']} totals={split['new_team_reset_mode_totals']}")
    if not differs:
        print("  WARNING: the two arms are IDENTICAL here — this fixture proves nothing")
    ok &= x_ok and t_ok

print("\nRESULT:", "PASS — split composes exactly" if ok else "FAIL")
sys.exit(0 if ok else 1)
