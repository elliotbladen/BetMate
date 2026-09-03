#!/usr/bin/env python3
"""Score the frozen Week-2 football prices with and without the player shadow.

The EPL portfolio called "Week 2" in BetMate is EPL matchweek 1.  The EFL
portfolio is Championship matchweek 2.  Both were frozen on 2026-08-19.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

import joblib
import numpy as np
import pandas as pd

from ml.football.player_layer.backfill_espn_player_stats import parse_match
from ml.football.player_layer.train_starter_shadow import ALIASES, ROLLING_STATS, ROLLING_WINDOW

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml" / "football" / "data" / "championship" / "player_layer"
SNAPSHOT = ROOT / "outputs" / "football" / "player_shadow_2026-08-19.json"
OUT = ROOT / "outputs" / "results" / "player_shadow_week2_2026-09-02.json"

EXTRA_ALIASES = {
    "Manchester City": "Man City", "Manchester United": "Man United",
    "Nottingham Forest": "Nott'm Forest", "Tottenham Hotspur": "Tottenham",
    "Brighton & Hove Albion": "Brighton", "AFC Bournemouth": "Bournemouth",
    "Crystal Palace": "Crystal Palace", "Aston Villa": "Aston Villa",
    "Arsenal": "Arsenal", "Chelsea": "Chelsea", "Liverpool": "Liverpool",
    "Newcastle United": "Newcastle", "Everton": "Everton", "Brentford": "Brentford",
    "Fulham": "Fulham",
}


def canon(name: str) -> str:
    return EXTRA_ALIASES.get(name, ALIASES.get(name, name))


def fetch_json(url: str) -> dict:
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
    })
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def ensure_epl_feeds() -> None:
    out = DATA / "match_feeds_epl"
    out.mkdir(parents=True, exist_ok=True)
    for day in ("20260821", "20260822", "20260823", "20260824"):
        board = fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates={day}")
        for event in board.get("events", []):
            path = out / f"{event['id']}.json"
            if not path.exists():
                payload = fetch_json(
                    f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event={event['id']}"
                )
                path.write_text(json.dumps(payload), encoding="utf-8")


def carry_forward() -> pd.DataFrame:
    frames = []
    for year in (2023, 2024, 2025):
        for suffix in ("", "_epl", "_league1"):
            path = DATA / f"player_match_stats_espn{suffix}_{year}.csv"
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


def feed_index(directory: Path) -> dict[tuple[str, str, str], Path]:
    index = {}
    for path in directory.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        header = payload.get("header", {}).get("competitions", [{}])[0]
        sides = {c.get("homeAway"): c for c in header.get("competitors", [])}
        if not {"home", "away"}.issubset(sides):
            continue
        key = (header.get("date", "")[:10], canon(sides["home"]["team"]["displayName"]),
               canon(sides["away"]["team"]["displayName"]))
        if "2026-08-21" <= key[0] <= "2026-08-24":
            index[key] = path
    return index


def features(payload: dict, event_id: str, carry: pd.DataFrame, columns: list[str]) -> tuple[dict, int]:
    starters = [r for r in parse_match(event_id, payload) if r["starter"]]
    row = {c: 0.0 for c in columns}
    matched = 0
    lookup = carry.set_index(carry.player_id.astype(str), drop=False)
    roll_cols = [f"roll_{s}_p90" for s in ROLLING_STATS] + ["roll_minutes"]
    for player in starters:
        pid = str(player["player_id"])
        if pid not in lookup.index or player["position_group"] == "SUB":
            continue
        matched += 1
        prior = lookup.loc[pid]
        if isinstance(prior, pd.DataFrame):
            prior = prior.iloc[-1]
        for col in roll_cols:
            key = f"{player['side']}_{player['position_group']}_{col}"
            if key in row:
                row[key] += float(prior.get(col, 0) or 0)
        key = f"{player['side']}_{player['position_group']}_count"
        if key in row:
            row[key] += 1
    return row, matched


def probabilities(home_lambda: float, away_lambda: float) -> dict[str, float]:
    goals = np.arange(13)
    hp = np.exp(-home_lambda) * np.power(home_lambda, goals) / np.array([math.factorial(int(x)) for x in goals])
    ap = np.exp(-away_lambda) * np.power(away_lambda, goals) / np.array([math.factorial(int(x)) for x in goals])
    matrix = np.outer(hp, ap)
    matrix /= matrix.sum()
    return {
        "H": float(np.tril(matrix, -1).sum()), "D": float(np.diag(matrix).sum()),
        "A": float(np.triu(matrix, 1).sum()),
        "over25": float(sum(matrix[h, a] for h in goals for a in goals if h + a > 2)),
        "btts": float(matrix[1:, 1:].sum()),
    }


def metrics(rows: list[dict], prefix: str) -> dict:
    ll, rps, acc, ou_ll, ou_brier, ou_acc, btts_ll, btts_brier, btts_acc = ([] for _ in range(9))
    for row in rows:
        p = row[prefix]
        result = row["result"]
        ll.append(-math.log(max(p[result], 1e-12)))
        y = [1 if result == x else 0 for x in "HDA"]
        rps.append(((p["H"] - y[0]) ** 2 + (p["H"] + p["D"] - y[0] - y[1]) ** 2) / 2)
        acc.append(max("HDA", key=lambda x: p[x]) == result)
        for key, actual, losses, briers, accuracies in (
            ("over25", row["goals"] > 2, ou_ll, ou_brier, ou_acc),
            ("btts", row["home_goals"] > 0 and row["away_goals"] > 0, btts_ll, btts_brier, btts_acc),
        ):
            prob = p[key]
            losses.append(-math.log(max(prob if actual else 1 - prob, 1e-12)))
            briers.append((prob - int(actual)) ** 2)
            accuracies.append((prob >= .5) == actual)
    mean = lambda x: float(np.mean(x))
    return {"matches": len(rows), "1x2_log_loss": mean(ll), "1x2_rps": mean(rps),
            "1x2_accuracy": mean(acc), "ou25_log_loss": mean(ou_ll), "ou25_brier": mean(ou_brier),
            "ou25_accuracy": mean(ou_acc), "btts_log_loss": mean(btts_ll),
            "btts_brier": mean(btts_brier), "btts_accuracy": mean(btts_acc)}


def main() -> None:
    ensure_epl_feeds()
    frozen = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["leagues"]
    model_blob = joblib.load(DATA / "player_shadow.joblib")
    model, columns, cap = model_blob["model"], model_blob["feature_cols"], model_blob["cap"]
    carry = carry_forward()
    output = {"source_snapshot": str(SNAPSHOT), "leagues": {}}
    for league, feed_dir in (("epl", "match_feeds_epl"), ("championship", "match_feeds")):
        feeds = feed_index(DATA / feed_dir)
        rows = []
        for game in frozen[league]["games"]:
            key = (game["kickoff"][:10], game["home"], game["away"])
            if key not in feeds:
                continue
            path = feeds[key]
            event_id, payload = path.stem, json.loads(path.read_text(encoding="utf-8"))
            header = payload["header"]["competitions"][0]
            sides = {c["homeAway"]: c for c in header["competitors"]}
            hg, ag = int(sides["home"]["score"]), int(sides["away"]["score"])
            feat, matched = features(payload, event_id, carry, columns)
            starter_count = sum(r["starter"] for r in parse_match(event_id, payload))
            if starter_count != 22:
                continue
            delta = np.clip(model.predict([[feat.get(c, 0.0) for c in columns]])[0], -cap, cap)
            base = probabilities(game["lambda_home"], game["lambda_away"])
            shadow = probabilities(max(.05, game["lambda_home"] + delta[0]),
                                   max(.05, game["lambda_away"] + delta[1]))
            rows.append({"home": game["home"], "away": game["away"], "score": f"{hg}-{ag}",
                         "home_goals": hg, "away_goals": ag, "goals": hg + ag,
                         "result": "H" if hg > ag else "D" if hg == ag else "A",
                         "starters_matched_to_history": matched,
                         "delta_home_goals": float(delta[0]), "delta_away_goals": float(delta[1]),
                         "base": base, "shadow": shadow})
        output["leagues"][league] = {"base": metrics(rows, "base"),
                                      "shadow": metrics(rows, "shadow"), "games": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
