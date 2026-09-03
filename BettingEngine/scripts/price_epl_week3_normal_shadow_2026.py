#!/usr/bin/env python3
"""Price EPL 2026/27 GW3 with production normal and comparison-only shadow."""
from __future__ import annotations

import contextlib
import io
import json
import math
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.football.price_match import price_match
from ml.football.player_layer.backfill_espn_player_stats import parse_match
from ml.football.player_layer.train_starter_shadow import ROLLING_STATS, ROLLING_WINDOW

ROOT = Path(__file__).resolve().parents[1]
PLAYER_DATA = ROOT / "ml" / "football" / "data" / "championship" / "player_layer"
FEEDS = PLAYER_DATA / "match_feeds_epl"
OUT_JSON = ROOT / "outputs" / "football" / "epl" / "gw3_normal_shadow_prices_2026-09-03.json"
OUT_MD = ROOT / "outputs" / "football" / "epl" / "gw3_normal_shadow_prices_2026-09-03.md"
OUT_WORKING = ROOT / "outputs" / "football" / "epl" / "gw3_normal_full_working_2026-09-03.txt"

FIXTURES = [
    ("2026-09-04", "Ipswich", "Liverpool"),
    ("2026-09-05", "Newcastle", "Bournemouth"),
    ("2026-09-05", "Brentford", "Sunderland"),
    ("2026-09-05", "Brighton", "Leeds"),
    ("2026-09-05", "Fulham", "Crystal Palace"),
    ("2026-09-05", "Man City", "Coventry"),
    ("2026-09-05", "Nott'm Forest", "Tottenham"),
    ("2026-09-05", "Hull", "Aston Villa"),
    ("2026-09-06", "Everton", "Man United"),
    ("2026-09-06", "Arsenal", "Chelsea"),
]

# Confirmed important first-team absences at the 2026-09-03 availability audit.
# Doubts are deliberately excluded until confirmed; names are retained in the
# report JSON while T5 consumes only the position codes below.
ABSENCES = {
    "Arsenal": [("William Saliba", "CB"), ("Jurrien Timber", "RB")],
    "Aston Villa": [("Amadou Onana", "DM"), ("Joao Gomes", "CM"), ("Leon Bailey", "RW")],
    "Bournemouth": [("Amine Adli", "AM"), ("Julian Araujo", "RB")],
    "Brentford": [("Antoni Milambo", "CM"), ("Sepp van den Berg", "CB")],
    "Brighton": [("Yankuba Minteh", "RW"), ("Jack Hinshelwood", "CM"),
                 ("Kaoru Mitoma", "LW"), ("Evan Ferguson", "ST")],
    "Chelsea": [("Enzo Fernandez", "CM")],
    "Coventry": [("Haji Wright", "ST"), ("Kaine Kesler-Hayden", "RB"),
                 ("Luke Woolfenden", "CB")],
    "Crystal Palace": [("Chadi Riad", "CB"), ("Jean-Philippe Mateta", "ST")],
    "Everton": [("Christian Norgaard", "DM")],
    "Fulham": [("Tom Cairney", "CM")],
    "Hull": [("Jack Butland", "GK"), ("Eliot Matazo", "CM"), ("Darko Gyabi", "CM"),
             ("Charlie Hughes", "CB"), ("Oscar Zambrano", "DM")],
    "Ipswich": [("Jaden Philogene", "LW"), ("Jack Taylor", "CM")],
    "Leeds": [("Joe Rodon", "CB"), ("Mateo Joseph", "ST")],
    "Liverpool": [("Conor Bradley", "RB"), ("Hugo Ekitike", "ST"),
                  ("Joe Gomez", "CB"), ("Giovanni Leoni", "CB")],
    "Man City": [("Jeremy Doku", "LW")],
    "Man United": [("Amad Diallo", "RW"), ("Carlos Baleba", "DM"),
                   ("Matthijs de Ligt", "CB"), ("Manuel Ugarte", "DM")],
    "Newcastle": [("Dan Burn", "CB"), ("Joelinton", "CM"), ("William Osula", "ST")],
    "Nott'm Forest": [("Nicolo Savona", "RB"), ("Ibrahim Sangare", "DM")],
    "Sunderland": [("Simon Adingra", "LW"), ("Dayann Methalie", "LB")],
    "Tottenham": [("Xavi Simons", "AM"), ("Wilson Odobert", "LW"),
                  ("Dejan Kulusevski", "AM")],
}

DOUBTS = {
    "Arsenal": ["Cristhian Mosquera (CB, 50%)"],
    "Aston Villa": ["Leon Goretzka (CM, 50%)"],
    "Brentford": ["Mathias Jensen (CM, 50%)"],
    "Brighton": ["Georginio Rutter (AM, 50%)", "Yasin Ayari (CM, 50%)"],
    "Chelsea": ["Moises Caicedo (DM, 50%)"],
    "Coventry": ["Frank Onyeka (DM, 50%)"],
    "Crystal Palace": ["Ismaila Sarr (RW, 25%)"],
    "Hull": ["Matt Crooks (AM, 50%)", "Lewie Coyle (RB, 50%)", "Joe Gelhardt (ST, 25%)"],
    "Ipswich": ["Azor Matusiwa (DM, 25%)", "Florentino Luis (DM, 50%)", "Emersonn (ST, 50%)"],
    "Leeds": ["Ilia Gruev (DM, 25%)"],
    "Liverpool": ["Federico Chiesa (FW, 25%)"],
    "Man City": ["Matheus Nunes (CM, 25%)"],
    "Newcastle": ["Tino Livramento (RB, 25%)"],
    "Sunderland": ["Habib Diarra (CM, 50%)"],
    "Tottenham": ["James Maddison (AM, 25%)", "Savio (RW, 50%)"],
}

ALIASES = {
    "AFC Bournemouth": "Bournemouth", "Brighton & Hove Albion": "Brighton",
    "Manchester City": "Man City", "Manchester United": "Man United",
    "Newcastle United": "Newcastle", "Nottingham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham", "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds", "Coventry City": "Coventry", "Hull City": "Hull",
}


def canon(name: str) -> str:
    return ALIASES.get(name, name)


def carry_forward() -> pd.DataFrame:
    frames = []
    for year in (2023, 2024, 2025):
        for suffix in ("", "_epl", "_league1"):
            path = PLAYER_DATA / f"player_match_stats_espn{suffix}_{year}.csv"
            if path.exists():
                frames.append(pd.read_csv(path))
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df.kickoff, utc=True)
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


def latest_starting_xis() -> dict[str, list[dict]]:
    latest: dict[str, tuple[str, list[dict]]] = {}
    for path in FEEDS.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        header = payload.get("header", {}).get("competitions", [{}])[0]
        date = header.get("date", "")
        if not date.startswith("2026-08"):
            continue
        for row in parse_match(path.stem, payload):
            if not row["starter"]:
                continue
            team = canon(row["team"])
            if team not in latest or date > latest[team][0]:
                latest[team] = (date, [])
            if date == latest[team][0]:
                latest[team][1].append(row)
    return {team: rows for team, (_, rows) in latest.items()}


def projected_features(home: str, away: str, xis: dict[str, list[dict]], carry: pd.DataFrame,
                       columns: list[str]) -> tuple[dict, dict]:
    values = {c: 0.0 for c in columns}
    lookup = carry.set_index(carry.player_id.astype(str), drop=False)
    meta = {"home_xi_count": len(xis.get(home, [])), "away_xi_count": len(xis.get(away, [])),
            "home_history_matches": 0, "away_history_matches": 0}
    roll_cols = [f"roll_{s}_p90" for s in ROLLING_STATS] + ["roll_minutes"]
    for side, team in (("home", home), ("away", away)):
        for player in xis.get(team, []):
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


def adjust_probabilities(normal: dict, lam: float, mu: float, shadow_lam: float, shadow_mu: float) -> dict:
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
    return round(1 / p, 2)


def main() -> None:
    blob = joblib.load(PLAYER_DATA / "player_shadow.joblib")
    carry, xis = carry_forward(), latest_starting_xis()
    games, working = [], []
    for date, home, away in FIXTURES:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            normal = price_match(
                home, away, as_of=datetime.fromisoformat(date), league="epl", matchweek=3,
                injuries_home=[pos for _, pos in ABSENCES.get(home, [])],
                injuries_away=[pos for _, pos in ABSENCES.get(away, [])],
            )
        if normal is None:
            raise RuntimeError(f"Normal engine did not price {home} v {away}")
        working.append(stream.getvalue())
        feat, coverage = projected_features(home, away, xis, carry, blob["feature_cols"])
        delta = np.clip(blob["model"].predict([[feat.get(c, 0.0) for c in blob["feature_cols"]]])[0],
                        -blob["cap"], blob["cap"])
        shadow_lam = max(.05, normal["lambda_home"] + float(delta[0]))
        shadow_mu = max(.05, normal["lambda_away"] + float(delta[1]))
        shadow = adjust_probabilities(normal, normal["lambda_home"], normal["lambda_away"], shadow_lam, shadow_mu)
        shadow.update({"lambda_home": shadow_lam, "lambda_away": shadow_mu,
                       "delta_home": float(delta[0]), "delta_away": float(delta[1]), **coverage})
        games.append({"date": date, "home": home, "away": away,
                      "confirmed_absences_home": ABSENCES.get(home, []),
                      "confirmed_absences_away": ABSENCES.get(away, []),
                      "doubts_home": DOUBTS.get(home, []), "doubts_away": DOUBTS.get(away, []),
                      "normal": normal, "shadow": shadow})

    payload = {"generated_at": datetime.now().isoformat(), "competition_matchweek": 3,
               "normal_status": "production", "shadow_status": "comparison_only_projected_last_xi",
               "limitations": [
                   "Shadow uses each club's most recent completed starting XI; official GW3 XIs are not yet available.",
                   "Understat xG and PPDA feeds end at 2024/25; later matches use the engine's documented goal fallback.",
                   "Confirmed important absences are injected into normal T5; doubts are excluded pending confirmation.",
                   "No current market odds or referee appointments were injected.",
               ], "games": games}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_WORKING.write_text("\n".join(working), encoding="utf-8")

    lines = ["# EPL Week 3 normal and player-shadow pricing", "", "Generated 3 September 2026.", "",
             "Normal is the production price. Shadow is comparison-only and uses the most recent completed XI as the projected lineup.", "",
             "## Price board", "",
             "| Match | Engine | xG H-A | H | D | A | O2.5 | U2.5 | BTTS Y | BTTS N |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for game in games:
        n, s = game["normal"], game["shadow"]
        btts = poisson_markets(n["lambda_home"], n["lambda_away"])["btts_yes"]
        lines.append(f"| {game['home']} v {game['away']} | **Normal** | {n['lambda_home']:.2f}-{n['lambda_away']:.2f} | {fair(n['p_home']):.2f} | {fair(n['p_draw']):.2f} | {fair(n['p_away']):.2f} | {fair(n['p_over25']):.2f} | {fair(n['p_under25']):.2f} | {fair(btts):.2f} | {fair(1-btts):.2f} |")
        lines.append(f"|  | Shadow | {s['lambda_home']:.2f}-{s['lambda_away']:.2f} | {fair(s['p_home']):.2f} | {fair(s['p_draw']):.2f} | {fair(s['p_away']):.2f} | {fair(s['p_over25']):.2f} | {fair(s['p_under25']):.2f} | {fair(s['p_btts_yes']):.2f} | {fair(s['p_btts_no']):.2f} |")
    lines += ["", "## Shadow adjustments and coverage", "",
              "| Match | Home delta | Away delta | Projected XI | Players with history |",
              "|---|---:|---:|---:|---:|"]
    for game in games:
        s = game["shadow"]
        lines.append(f"| {game['home']} v {game['away']} | {s['delta_home']:+.3f} xG | {s['delta_away']:+.3f} xG | {s['home_xi_count']}+{s['away_xi_count']} | {s['home_history_matches']}+{s['away_history_matches']} |")
    lines += ["", "## Working and limitations", "",
              "The full normal-engine calculation for every match—including D-C base xG, Elo, current form, rest, corners and every fired tier—is saved in the companion working file.", "",
              "Confirmed important absences from the 3 September audit are included in normal-engine T5. Doubts are excluded pending late fitness confirmation. Referee appointments and live market odds were not injected. Re-price after official team news and final XIs; do not treat the provisional shadow prices as betting approval.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
