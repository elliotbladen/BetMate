#!/usr/bin/env python3
"""Price EFL Championship 2026/27 GW7 — production normal + comparison-only shadow.

Same structure as `price_epl_week4_normal_shadow_2026.py`, retargeted at E1:

  * GW7 fixture list (11-13 Sep 2026). GW6 (8-9 Sep) is already played; three of
    its fixtures were postponed, so six clubs arrive on 5 games and eighteen on 6.
    `matchweek` is passed per fixture as the games that club has actually played,
    because T8's prior weight is a per-team decay, not a calendar week.
  * Championship is GOALS-FED (`xg_csv: null`), so the EPL xG scale-break that
    inflates EPL totals does not apply here. Verified in-run.
  * Market 1X2 AND Over/Under 2.5 are both available from the live Odds API
    snapshot, so EV is computed for both markets.
  * Shadow reads each club's most recent completed starting XI from the 2026/27
    Championship feeds and a current-season player-stats file.
  * T6 referee left un-injected — the EFL had not published GW7 appointments at
    build time (ESPN `gameInfo.officials` is null on all 12 fixtures).
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.football.price_match import price_match  # noqa: E402
from ml.football.player_layer.backfill_espn_player_stats import parse_match  # noqa: E402
from ml.football.player_layer.train_starter_shadow import ROLLING_STATS, ROLLING_WINDOW  # noqa: E402

PLAYER_DATA = ROOT / "ml" / "football" / "data" / "championship" / "player_layer"
FEEDS = PLAYER_DATA / "match_feeds"
OUTDIR = ROOT / "outputs" / "football" / "championship" / "2026-27" / "gw07"
SUPPORT = OUTDIR / "_supporting"

FIXTURES = [
    ("2026-09-11", "West Ham", "Wrexham"),
    ("2026-09-12", "Bolton", "Cardiff"),
    ("2026-09-12", "Derby", "Birmingham"),
    ("2026-09-12", "West Brom", "QPR"),
    ("2026-09-12", "Blackburn", "Millwall"),
    ("2026-09-12", "Charlton", "Portsmouth"),
    ("2026-09-12", "Middlesbrough", "Norwich"),
    ("2026-09-12", "Preston", "Lincoln"),
    ("2026-09-12", "Southampton", "Bristol City"),
    ("2026-09-12", "Swansea", "Burnley"),
    ("2026-09-12", "Watford", "Stoke"),
    ("2026-09-13", "Sheffield United", "Wolves"),
]

# Games each club has completed in 2026/27 before this round -> T8 prior weight.
GAMES_PLAYED = {
    "Birmingham": 6, "Blackburn": 6, "Bolton": 6, "Bristol City": 5, "Burnley": 6,
    "Cardiff": 6, "Charlton": 6, "Derby": 6, "Lincoln": 5, "Middlesbrough": 5,
    "Millwall": 5, "Norwich": 6, "Portsmouth": 5, "Preston": 6, "QPR": 6,
    "Sheffield United": 6, "Southampton": 6, "Stoke": 6, "Swansea": 6,
    "Watford": 6, "West Brom": 6, "West Ham": 6, "Wolves": 5, "Wrexham": 6,
}

# Live market, Odds API snapshot 2026-09-10 13:29 UTC.
# "avg" = mean across the ~28 non-exchange books carrying the fixture (EV reference).
# "best" = best price at any of those books. Exchanges excluded (gross of commission).
MARKET = json.loads((Path(__file__).resolve().parent / "_efl_gw7_market_2026.json").read_text())

# Confirmed absences at the availability audit. Positions only — T5 treats each
# entry as a full positional absence, so doubts are excluded, not part-weighted.
ABSENCES: dict[str, list[tuple[str, str]]] = json.loads(
    (Path(__file__).resolve().parent / "_efl_gw7_absences_2026.json").read_text()
)
DOUBTS: dict[str, list[str]] = json.loads(
    (Path(__file__).resolve().parent / "_efl_gw7_doubts_2026.json").read_text()
)

# T9 new-manager bounce: clubs whose manager was appointed inside the window.
NEW_MANAGERS: set[str] = set()

ALIASES = {
    "Blackburn Rovers": "Blackburn", "Bolton Wanderers": "Bolton",
    "Bristol City": "Bristol City", "Cardiff City": "Cardiff",
    "Charlton Athletic": "Charlton", "Derby County": "Derby",
    "Lincoln City": "Lincoln", "Norwich City": "Norwich",
    "Preston North End": "Preston", "Queens Park Rangers": "QPR",
    "Sheffield United": "Sheffield United", "Stoke City": "Stoke",
    "Swansea City": "Swansea", "West Bromwich Albion": "West Brom",
    "West Ham United": "West Ham", "Wolverhampton Wanderers": "Wolves",
    "Birmingham City": "Birmingham", "Wrexham": "Wrexham",
    "Middlesbrough": "Middlesbrough", "Millwall": "Millwall",
    "Southampton": "Southampton", "Watford": "Watford",
    "Burnley": "Burnley", "Portsmouth": "Portsmouth",
}


def canon(name: str) -> str:
    return ALIASES.get(name, name)


def carry_forward() -> pd.DataFrame:
    """Latest rolling per-90 form row per player, across E1/E0/L1 feeds."""
    frames = []
    for year in (2023, 2024, 2025, 2026):
        for suffix in ("", "_epl", "_league1"):
            path = PLAYER_DATA / f"player_match_stats_espn{suffix}_{year}.csv"
            if path.exists():
                frames.append(pd.read_csv(path))
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(["event_id", "player_id"])
    df["date"] = pd.to_datetime(df.kickoff, utc=True, format="mixed")
    df = df.sort_values(["player_id", "date"])
    for stat in ROLLING_STATS:
        col = f"{stat}_p90"
        df[col] = np.where(df.minutes > 0, df[stat] / df.minutes * 90, 0.0)
        df[f"roll_{col}"] = df.groupby("player_id")[col].transform(
            lambda x: x.rolling(ROLLING_WINDOW, min_periods=1).mean()
        )
    df["roll_minutes"] = df.groupby("player_id")["minutes"].transform(
        lambda x: x.rolling(ROLLING_WINDOW, min_periods=1).mean()
    )
    return df.groupby("player_id", as_index=False).last()


def latest_starting_xis() -> dict[str, tuple[str, list[dict]]]:
    """Most recent completed 2026/27 starting XI per club."""
    latest: dict[str, tuple[str, list[dict]]] = {}
    for path in FEEDS.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        header = payload.get("header", {}).get("competitions", [{}])[0]
        date = header.get("date", "")
        if not (date.startswith("2026-08") or date.startswith("2026-09")):
            continue
        if not header.get("status", {}).get("type", {}).get("completed"):
            continue
        for row in parse_match(path.stem, payload):
            if not row["starter"]:
                continue
            team = canon(row["team"])
            if team not in latest or date > latest[team][0]:
                latest[team] = (date, [])
            if date == latest[team][0]:
                latest[team][1].append(row)
    return latest


def projected_features(home, away, xis, carry, columns):
    values = {c: 0.0 for c in columns}
    lookup = carry.set_index(carry.player_id.astype(str), drop=False)
    meta = {"home_xi_count": len(xis.get(home, ("", []))[1]),
            "away_xi_count": len(xis.get(away, ("", []))[1]),
            "home_xi_date": xis.get(home, ("", []))[0][:10],
            "away_xi_date": xis.get(away, ("", []))[0][:10],
            "home_history_matches": 0, "away_history_matches": 0}
    roll_cols = [f"roll_{s}_p90" for s in ROLLING_STATS] + ["roll_minutes"]
    for side, team in (("home", home), ("away", away)):
        for player in xis.get(team, ("", []))[1]:
            pid = str(player["player_id"])
            if pid not in lookup.index or player["position_group"] == "SUB":
                continue
            meta[f"{side}_history_matches"] += 1
            prior = lookup.loc[pid]
            if isinstance(prior, pd.DataFrame):
                prior = prior.iloc[-1]
            pg = player["position_group"]
            for col in roll_cols:
                key = f"{side}_{pg}_{col}"
                if key in values:
                    values[key] += float(prior.get(col, 0) or 0)
            key = f"{side}_{pg}_count"
            if key in values:
                values[key] += 1
    return values, meta


def poisson_markets(lam: float, mu: float) -> dict[str, float]:
    goals = np.arange(13)
    fact = np.array([math.factorial(int(x)) for x in goals])
    hp = np.exp(-lam) * lam ** goals / fact
    ap = np.exp(-mu) * mu ** goals / fact
    matrix = np.outer(hp, ap)
    matrix /= matrix.sum()
    return {"home": float(np.tril(matrix, -1).sum()), "draw": float(np.diag(matrix).sum()),
            "away": float(np.triu(matrix, 1).sum()),
            "over25": float(sum(matrix[h, a] for h in goals for a in goals if h + a > 2)),
            "btts_yes": float(matrix[1:, 1:].sum())}


def adjust_probabilities(normal, lam, mu, shadow_lam, shadow_mu):
    base_raw, shadow_raw = poisson_markets(lam, mu), poisson_markets(shadow_lam, shadow_mu)
    weights = {k: normal[f"p_{k}"] * shadow_raw[k] / base_raw[k] for k in ("home", "draw", "away")}
    total = sum(weights.values())
    out = {f"p_{k}": weights[k] / total for k in weights}
    p = normal["p_over25"]
    base_odds = base_raw["over25"] / (1 - base_raw["over25"])
    adj_odds = shadow_raw["over25"] / (1 - shadow_raw["over25"])
    calibrated_odds = p / (1 - p) * adj_odds / base_odds
    out["p_over25"] = calibrated_odds / (1 + calibrated_odds)
    out["p_under25"] = 1 - out["p_over25"]
    out["p_btts_yes"] = shadow_raw["btts_yes"]
    out["p_btts_no"] = 1 - shadow_raw["btts_yes"]
    return out


def fair(p: float) -> float:
    return round(1 / p, 2) if p > 0 else float("inf")


def devig(odds: tuple[float, ...]) -> tuple[float, ...]:
    raw = [1.0 / o for o in odds]
    s = sum(raw)
    return tuple(r / s for r in raw)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    SUPPORT.mkdir(parents=True, exist_ok=True)
    blob = joblib.load(PLAYER_DATA / "player_shadow.joblib")
    carry, xis = carry_forward(), latest_starting_xis()
    games, working = [], []

    for date, home, away in FIXTURES:
        mkt = MARKET[f"{home} v {away}"]
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            normal = price_match(
                home, away, as_of=datetime.fromisoformat(date), league="championship",
                matchweek=GAMES_PLAYED[home],
                injuries_home=[pos for _, pos in ABSENCES.get(home, [])],
                injuries_away=[pos for _, pos in ABSENCES.get(away, [])],
                mkt_home=mkt["avg_home"], mkt_draw=mkt["avg_draw"], mkt_away=mkt["avg_away"],
                mkt_over25=mkt["avg_over25"],
                new_manager_home=home in NEW_MANAGERS,
                new_manager_away=away in NEW_MANAGERS,
            )
        if normal is None:
            raise RuntimeError(f"Normal engine did not price {home} v {away}")
        working.append(stream.getvalue())

        feat, coverage = projected_features(home, away, xis, carry, blob["feature_cols"])
        delta = np.clip(blob["model"].predict([[feat.get(c, 0.0) for c in blob["feature_cols"]]])[0],
                        -blob["cap"], blob["cap"])
        shadow_lam = max(.05, normal["lambda_home"] + float(delta[0]))
        shadow_mu = max(.05, normal["lambda_away"] + float(delta[1]))
        shadow = adjust_probabilities(normal, normal["lambda_home"], normal["lambda_away"],
                                      shadow_lam, shadow_mu)
        shadow.update({"lambda_home": shadow_lam, "lambda_away": shadow_mu,
                       "delta_home": float(delta[0]), "delta_away": float(delta[1]), **coverage})

        nv_1x2 = devig((mkt["avg_home"], mkt["avg_draw"], mkt["avg_away"]))
        nv_ou = devig((mkt["avg_over25"], mkt["avg_under25"]))
        games.append({
            "date": date, "home": home, "away": away,
            "games_played_home": GAMES_PLAYED[home], "games_played_away": GAMES_PLAYED[away],
            "market": mkt,
            "market_novig": {"home": nv_1x2[0], "draw": nv_1x2[1], "away": nv_1x2[2],
                             "over25": nv_ou[0], "under25": nv_ou[1]},
            "dc_reset_teams": normal.get("new_team_resets") or [],
            "confirmed_absences_home": ABSENCES.get(home, []),
            "confirmed_absences_away": ABSENCES.get(away, []),
            "doubts_home": DOUBTS.get(home, []), "doubts_away": DOUBTS.get(away, []),
            "normal": normal, "shadow": shadow,
        })

    payload = {
        "generated_at": datetime.now().isoformat(),
        "league": "championship", "season": "2026/27", "competition_matchweek": 7,
        "normal_status": "production",
        "shadow_status": "comparison_only_projected_last_xi",
        "limitations": [
            "GW6 (8-9 Sep) results were absent from football-data.co.uk at build time and were "
            "supplemented from ESPN (9 matches, scores/refs/shots/corners/cards only, no odds). "
            "Without them the engine reported 7-day rest for every club and missed a full round.",
            "Three GW6 fixtures were postponed, so Bristol City, Lincoln, Middlesbrough, Millwall, "
            "Portsmouth and Wolves arrive on 5 games rather than 6.",
            "T6 referee not injected - the EFL had not published GW7 appointments at build time.",
            "T2 PPDA runs on the matchweek-1 FBref seed (16-17 Aug); ppda_dated.csv has no later "
            "2026/27 rows and get_ppda has no recency guard.",
            "Shadow uses each club's most recent completed starting XI (GW6 where played, else GW5).",
            "D-C ratings for the six clubs new to the division are forced to league average by "
            "_reset_new_team_dc_ratings, discarding their 2026/27 results. See the reset sensitivity.",
        ],
        "games": games,
    }
    (OUTDIR / "1_model.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (SUPPORT / "normal_full_working.txt").write_text("\n".join(working), encoding="utf-8")
    print(f"wrote {OUTDIR / '1_model.json'}")
    for g in games:
        n, s, m = g["normal"], g["shadow"], g["market_novig"]
        flag = "R" if g["dc_reset_teams"] else " "
        print(f"{flag} {g['home']:<17}v {g['away']:<15} "
              f"N {n['lambda_home']:.2f}-{n['lambda_away']:.2f} "
              f"H{fair(n['p_home']):>6.2f} D{fair(n['p_draw']):>6.2f} A{fair(n['p_away']):>6.2f} "
              f"O{fair(n['p_over25']):>5.2f} | S H{fair(s['p_home']):>6.2f} "
              f"D{fair(s['p_draw']):>6.2f} A{fair(s['p_away']):>6.2f} O{fair(s['p_over25']):>5.2f} "
              f"| mktO {m['over25']:.3f} mdlO {n['p_over25']:.3f}")


if __name__ == "__main__":
    main()
