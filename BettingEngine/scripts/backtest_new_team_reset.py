#!/usr/bin/env python3
"""Walk-forward A/B of the new-team D-C reset, scored per the pre-registration.

Rules, metric and decision threshold were fixed in
outputs/football/championship/_research/RESET_FIX_PREREGISTRATION.md and committed
BEFORE this harness existed. Do not edit the metric here.

Scores the SPINE only (D-C blended with Elo, exactly as price_match blends them).
Tiers are excluded because T5 injury lists and T6 referee profiles do not exist for
past seasons. O/U is scored on the raw D-C probability: the production isotonic
calibrator is a separate, known-flat component we agreed not to touch, and applying
it would compress the very difference being measured.

Usage:
    python scripts/backtest_new_team_reset.py --validate-scorer
    python scripts/backtest_new_team_reset.py --seasons 2015/16 2024/25
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.football.league_config import load_league                      # noqa: E402
from ml.football.models.dixon_coles import (                           # noqa: E402
    expected_goals, build_scoreline_matrix, derive_markets, fit as dc_fit)
from ml.football.models.elo import build_from_history                  # noqa: E402
from ml.football.price_match import _reset_new_team_dc_ratings, load_data  # noqa: E402

EPS = 1e-12
MODES = ("league_average", "shrunk_current_season", "elo_seeded", "elo_seeded_level_neutral")
TAG = {"league_average": "old", "shrunk_current_season": "shr", "elo_seeded": "elo",
       "elo_seeded_level_neutral": "eln"}
OUT = ROOT / "outputs/football/championship/_research"


def surprise(p: float) -> float:
    """-log(probability the model gave to what actually happened). Lower is better."""
    return -math.log(max(float(p), EPS))


# ── scorer validation on known answers ────────────────────────────────────────
def validate_scorer() -> bool:
    """The pre-registration requires this to pass before any result is trusted."""
    ok = True
    perfect = np.mean([surprise(1.0) for _ in range(50)])
    uniform = np.mean([surprise(1 / 3) for _ in range(50)])
    confident_wrong = surprise(0.01)
    print("Scorer validation (lower = better):")
    print(f"  certainty on the true result : {perfect:.4f}   expect ~0")
    print(f"  every outcome equally likely : {uniform:.4f}   expect ~1.0986")
    print(f"  1% on what actually happened : {confident_wrong:.4f}   expect ~4.605")
    if not abs(perfect) < 1e-6:
        print("  FAIL: a certain correct call did not score ~0"); ok = False
    if not abs(uniform - math.log(3)) < 1e-6:
        print("  FAIL: the uniform model did not score log(3)"); ok = False
    if not confident_wrong > uniform > perfect:
        print("  FAIL: ordering is wrong"); ok = False
    print("  PASS — ordering and magnitudes correct\n" if ok else "  BROKEN\n")
    return ok


def devig(odds: list[float]) -> list[float] | None:
    if any(o is None or not np.isfinite(o) or o <= 1.0 for o in odds):
        return None
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return [i / s for i in inv]


def season_of(label: str) -> int:
    return int(label.split("/")[0])


def run(seasons: list[str], cfg, df: pd.DataFrame) -> dict:
    rho = float(cfg.model["rho"])
    decay = float(cfg.model["decay_rate"])
    dcw, elow = float(cfg.model["dc_weight"]), float(cfg.model["elo_weight"])
    rows = []

    for season in seasons:
        prev = f"{season_of(season) - 1}/{str(season_of(season))[-2:]}"
        prev_teams = set(df[df.Season == prev].HomeTeam) | set(df[df.Season == prev].AwayTeam)
        if not prev_teams:
            print(f"  {season}: no prior season in file — skipped")
            continue
        cur = df[df.Season == season].sort_values("Date")
        teams = set(cur.HomeTeam) | set(cur.AwayTeam)
        new_clubs = sorted(teams - prev_teams)
        target = cur[cur.HomeTeam.isin(new_clubs) | cur.AwayTeam.isin(new_clubs)]
        print(f"  {season}: {len(new_clubs)} new clubs, {len(target)} affected fixtures", flush=True)

        for date, day in target.groupby("Date"):
            hist = df[df.Date < date]
            if len(hist) < 200:
                continue
            with contextlib.redirect_stdout(io.StringIO()):
                base = dc_fit(hist.rename(columns={"HomeTeam": "home_team",
                                                   "AwayTeam": "away_team"}),
                              as_of=date, rho=rho, decay_rate=decay)
                elo = build_from_history(hist, as_of=date, **cfg.elo)
            if not base or "attack" not in base:
                continue
            variants = {}
            for mode in MODES:
                variants[mode] = _reset_new_team_dc_ratings(
                    base, df, new_clubs, date.to_pydatetime(), mode=mode,
                    shrink_games=float(cfg.model.get("new_team_shrink_games", 6.0)),
                    rho=rho, elo_ratings=getattr(elo, "ratings", None))

            for m in day.itertuples():
                if m.HomeTeam not in base["attack"] or m.AwayTeam not in base["attack"]:
                    continue
                if not np.isfinite(m.FTHG) or not np.isfinite(m.FTAG):
                    continue
                actual = "H" if m.FTHG > m.FTAG else ("A" if m.FTAG > m.FTHG else "D")
                over = (m.FTHG + m.FTAG) > 2.5
                try:
                    em = elo.win_probabilities(m.HomeTeam, m.AwayTeam)
                except Exception:
                    continue
                rec = {"season": season, "date": date.date().isoformat(),
                       "home": m.HomeTeam, "away": m.AwayTeam,
                       "actual": actual, "over": bool(over)}
                for mode, r in variants.items():
                    lam, mu = expected_goals(m.HomeTeam, m.AwayTeam, r)
                    mk = derive_markets(build_scoreline_matrix(lam, mu, rho=rho))
                    ph = dcw * mk["p_home"] + elow * em["p_home"]
                    pdw = dcw * mk["p_draw"] + elow * em["p_draw"]
                    pa = dcw * mk["p_away"] + elow * em["p_away"]
                    s = ph + pdw + pa
                    ph, pdw, pa = ph / s, pdw / s, pa / s
                    po = float(mk["p_over25"])
                    tag = TAG[mode]
                    rec[f"{tag}_1x2"] = surprise({"H": ph, "D": pdw, "A": pa}[actual])
                    rec[f"{tag}_ou"] = surprise(po if over else 1 - po)
                    rec[f"{tag}_lam"] = lam + mu
                # Market reference (reported, NOT part of the verdict).
                # Pinnacle closing (PSC*) is the only triple that covers every season:
                # AvgC* is empty before 2019/20, and PSC* is empty for 2026/27. Reading
                # Avg* for an old season silently yields NaN — the same trap already
                # recorded for the totals columns in DATA_INTEGRITY_LESSONS.
                mp = None
                for trio in (("PSCH", "PSCD", "PSCA"), ("AvgCH", "AvgCD", "AvgCA"),
                             ("B365H", "B365D", "B365A")):
                    mp = devig([getattr(m, c, np.nan) for c in trio])
                    if mp:
                        rec["mkt_src"] = trio[0]
                        break
                if mp:
                    rec["mkt_1x2"] = surprise(dict(zip("HDA", mp))[actual])
                rows.append(rec)
    return {"rows": rows}


def report(rows: list[dict]) -> dict:
    df = pd.DataFrame(rows)
    if df.empty:
        print("no rows scored"); return {}
    n_seasons = df.season.nunique()
    out = {"n_games": len(df), "n_seasons": int(n_seasons), "variants": {}}

    print(f"\n{'season':<10}{'n':>5}" +
          "".join(f"{t+' 1X2':>11}" for t in ("old", "shr", "elo", "eln")) +
          "".join(f"{t+' O/U':>11}" for t in ("old", "shr", "elo", "eln")) + f"{'mkt 1X2':>11}")
    print("-" * 130)
    wins = {t: {"1x2": 0, "ou": 0} for t in ("shr", "elo", "eln")}
    for season, g in df.groupby("season"):
        line = f"{season:<10}{len(g):>5}"
        for t in ("old", "shr", "elo", "eln"):
            line += f"{g[f'{t}_1x2'].mean():>11.4f}"
        for t in ("old", "shr", "elo", "eln"):
            line += f"{g[f'{t}_ou'].mean():>11.4f}"
        mk = g.mkt_1x2.mean() if "mkt_1x2" in g and g.mkt_1x2.notna().any() else float("nan")
        line += f"{mk:>11.4f}"
        print(line)
        for t in ("shr", "elo", "eln"):
            wins[t]["1x2"] += g[f"{t}_1x2"].mean() < g.old_1x2.mean()
            wins[t]["ou"] += g[f"{t}_ou"].mean() < g.old_ou.mean()
    print("-" * 130)
    line = f"{'POOLED':<10}{len(df):>5}"
    for t in ("old", "shr", "elo", "eln"):
        line += f"{df[f'{t}_1x2'].mean():>11.4f}"
    for t in ("old", "shr", "elo", "eln"):
        line += f"{df[f'{t}_ou'].mean():>11.4f}"
    line += f"{df.mkt_1x2.mean() if 'mkt_1x2' in df else float('nan'):>11.4f}"
    print(line)

    print("\nvs league_average baseline (negative = better):")
    for t, label in (("shr", "shrunk_current_season"), ("elo", "elo_seeded"),
                     ("eln", "elo_seeded_level_neutral")):
        d1 = df[f"{t}_1x2"].mean() - df.old_1x2.mean()
        d2 = df[f"{t}_ou"].mean() - df.old_ou.mean()
        print(f"  {label:<24} 1X2 {d1:+.4f} ({wins[t]['1x2']}/{n_seasons} seasons)   "
              f"O/U {d2:+.4f} ({wins[t]['ou']}/{n_seasons} seasons)")
        out["variants"][label] = {"d_1x2": d1, "d_ou": d2,
                                  "seasons_won_1x2": int(wins[t]["1x2"]),
                                  "seasons_won_ou": int(wins[t]["ou"]),
                                  "pooled_1x2": df[f"{t}_1x2"].mean(),
                                  "pooled_ou": df[f"{t}_ou"].mean()}
    out["baseline"] = {"pooled_1x2": df.old_1x2.mean(), "pooled_ou": df.old_ou.mean(),
                       "market_1x2": float(df.mkt_1x2.mean()) if "mkt_1x2" in df else None}
    out["lam"] = {t: float(df[f"{t}_lam"].mean()) for t in ("old", "shr", "elo", "eln")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs=2, default=["2015/16", "2024/25"],
                    metavar=("FROM", "TO"))
    ap.add_argument("--validate-scorer", action="store_true")
    args = ap.parse_args()

    if not validate_scorer():
        print("Scorer failed its own checks — refusing to run the comparison.")
        return 2
    if args.validate_scorer:
        return 0

    cfg = load_league("championship")
    with contextlib.redirect_stdout(io.StringIO()):
        df, _, _ = load_data(cfg)
    lo, hi = season_of(args.seasons[0]), season_of(args.seasons[1])
    seasons = [s for s in sorted(df.Season.dropna().unique())
               if lo <= season_of(s) <= hi and s != "2025/26"]
    print(f"Scoring {len(seasons)} seasons: {seasons[0]} .. {seasons[-1]}"
          f"   (2025/26 vault excluded)\n")
    res = run(seasons, cfg, df)
    summary = report(res["rows"])
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(res["rows"]).to_csv(OUT / "new_team_reset_backtest.csv", index=False)
    (OUT / "new_team_reset_backtest.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"\nwrote {OUT/'new_team_reset_backtest.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
