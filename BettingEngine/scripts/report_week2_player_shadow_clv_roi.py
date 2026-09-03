#!/usr/bin/env python3
"""Hypothetical Week-2 CLV/ROI: base Poisson versus player shadow."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs" / "results"
SHADOW = RESULTS / "player_shadow_week2_2026-09-02.json"
OUT_JSON = RESULTS / "player_shadow_week2_clv_roi_2026-09-03.json"
OUT_MD = RESULTS / "player_shadow_week2_clv_roi_2026-09-03.md"

SOURCES = {
    "epl": {
        "1x2": RESULTS / "all model results" / "epl_week1_1x2_all_predictions.csv",
        "ou25": RESULTS / "all model results" / "epl_week1_ou25_all_predictions.csv",
    },
    "championship": {
        "1x2": RESULTS / "all model results" / "efl_championship_week2_1x2_all_predictions.csv",
        "ou25": RESULTS / "all model results" / "efl_championship_week2_ou25_all_predictions.csv",
    },
}


def market_rows(path: Path) -> dict[tuple[str, str], list[dict]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["home"], row["away"]), []).append(row)
    return grouped


def selection(game: dict, rows: list[dict], model: str, market: str) -> dict:
    probs = game[model]
    candidates = []
    for row in rows:
        side = row["side"]
        key = side if market == "1x2" else "over25" if side == "Over" else "under25"
        prob = probs[key] if key != "under25" else 1 - probs["over25"]
        opening, closing = float(row["opening_odds"]), float(row["closing_odds"])
        candidates.append({
            "side": side, "selection": row["selection"], "probability": prob,
            "opening_odds": opening, "closing_odds": closing,
            "ev": prob * opening - 1,
            "clv": opening / closing - 1,
            "won": bool(int(row["won"])),
        })
    chosen = max(candidates, key=lambda x: x["ev"])
    chosen.update({"home": game["home"], "away": game["away"], "score": game["score"],
                   "market": market, "model": model})
    chosen["opening_profit"] = chosen["opening_odds"] - 1 if chosen["won"] else -1
    chosen["closing_profit"] = chosen["closing_odds"] - 1 if chosen["won"] else -1
    return chosen


def summary(bets: list[dict]) -> dict:
    n = len(bets)
    return {
        "bets": n,
        "wins": sum(x["won"] for x in bets),
        "mean_ev": sum(x["ev"] for x in bets) / n if n else None,
        "mean_clv": sum(x["clv"] for x in bets) / n if n else None,
        "positive_clv": sum(x["clv"] > 0 for x in bets),
        "opening_profit": sum(x["opening_profit"] for x in bets),
        "opening_roi": sum(x["opening_profit"] for x in bets) / n if n else None,
        "closing_profit": sum(x["closing_profit"] for x in bets),
        "closing_roi": sum(x["closing_profit"] for x in bets) / n if n else None,
    }


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.1%}"


def main() -> None:
    data = json.loads(SHADOW.read_text(encoding="utf-8"))["leagues"]
    report = {"method": {
        "selection": "Largest positive expected-value side at opening odds, one candidate per fixture/market",
        "staking": "Flat 1 unit",
        "clv": "opening_odds / closing_odds - 1",
        "note": "Hypothetical retrospective comparison; these were not player-shadow bets actually placed",
    }, "leagues": {}}
    for league, sources in SOURCES.items():
        games = data[league]["games"]
        league_out = {}
        for market, source in sources.items():
            markets = market_rows(source)
            bets = {"base": [], "shadow": []}
            for game in games:
                rows = markets.get((game["home"], game["away"]))
                if not rows:
                    continue
                for model in bets:
                    bet = selection(game, rows, model, market)
                    if bet["ev"] > 0:
                        bets[model].append(bet)
            league_out[market] = {}
            for model, all_bets in bets.items():
                league_out[market][model] = {
                    "all_positive_edge": summary(all_bets),
                    "ev_10_percent": summary([x for x in all_bets if x["ev"] >= .10]),
                    "bets": all_bets,
                }
        report["leagues"][league] = league_out
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = ["# Week 2 player-shadow CLV and ROI", "",
             "Hypothetical flat one-unit comparison. The selected side is the largest positive model EV at Football-Data average opening odds. CLV is opening odds divided by closing odds minus one.", ""]
    for league, league_data in report["leagues"].items():
        lines += [f"## {league.upper()}", "",
                  "| Market | Filter | Engine | Bets | Wins | Mean CLV | +CLV | Opening P/L | Opening ROI | Closing ROI |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for market, models in league_data.items():
            for filt in ("all_positive_edge", "ev_10_percent"):
                for model in ("base", "shadow"):
                    s = models[model][filt]
                    lines.append(f"| {market} | {filt} | {model} | {s['bets']} | {s['wins']} | {pct(s['mean_clv'])} | {s['positive_clv']}/{s['bets']} | {s['opening_profit']:+.2f}u | {pct(s['opening_roi'])} | {pct(s['closing_roi'])} |")
        lines.append("")
    lines += ["## Interpretation", "",
              "This is a diagnostic, not an actual-bets ledger. A one-round ROI result is highly volatile; CLV is the more useful early signal, while promotion of the shadow engine requires a much larger prospective sample.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
