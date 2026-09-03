"""Opening/closing market audit for the two saved EPL/EFL performance weeks."""
from __future__ import annotations

from pathlib import Path
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

LEAGUES = {
    "EPL": ROOT / "ml/football/data/epl/matches/epl_matches.csv",
    "EFL Championship": ROOT / "ml/football/data/championship/matches/championship_matches.csv",
}


def week1_rows(league: str) -> list[dict]:
    folder = "epl" if league == "EPL" else "championship"
    paths = [
        (ROOT / f"outputs/football/{folder}/gw1_clv_backtest_2026-08-26.csv", "1X2"),
        (ROOT / f"outputs/football/{folder}/gw1_ou25_clv_backtest_2026-08-26.csv", "O/U 2.5"),
    ]
    rows = []
    for path, market in paths:
        frame = pd.read_csv(path)
        for item in frame[frame["ev"] >= 0.10 - 1e-12].to_dict("records"):
            home, away = item["game"].split(" v ", 1)
            side = str(item["side"])
            selection = ({"H": f"{home} win", "D": "Draw", "A": f"{away} win"}.get(side)
                         if market == "1X2" else f"{side} 2.5")
            rows.append({"week": 1, "league": league, "home": home, "away": away,
                         "market": market, "selection": selection, "side": side,
                         "model_prob": float(item["model_prob"]),
                         "reference_price": float(item["close_odds"]),
                         "price_status": "prior report closing quote; no placement ledger"})
    return rows


def week2_rows() -> list[dict]:
    jobs = [
        ("EPL", ROOT / "outputs/football/epl/gw2_bets_2026-08-31.csv"),
        ("EFL Championship", ROOT / "outputs/football/championship/gw3_bets_2026-08-31.csv"),
    ]
    rows = []
    for league, path in jobs:
        for item in pd.read_csv(path).to_dict("records"):
            selection = item["selection"]
            side = ("H" if selection.lower().startswith(str(item["home"]).lower()) else
                    "A" if selection.lower().startswith(str(item["away"]).lower()) else
                    "D" if "draw" in selection.lower() else
                    "Over" if selection.lower().startswith("over") else "Under")
            rows.append({"week": 2, "league": league, "home": item["home"], "away": item["away"],
                         "market": item["market"], "selection": selection, "side": side,
                         "model_prob": float(item["normal_probability"]),
                         "reference_price": float(item["saved_price"]),
                         "price_status": str(item["status"])})
    return rows


def valid(values) -> bool:
    return all(value is not None and not pd.isna(value) and float(value) > 1 for value in values)


def market_prices(result: pd.Series, market: str, side: str):
    if market == "1X2":
        open_cols = ["AvgH", "AvgD", "AvgA"]
        close_cols = ["AvgCH", "AvgCD", "AvgCA"]
        index = {"H": 0, "D": 1, "A": 2}[side]
    else:
        open_cols = ["Avg>2.5", "Avg<2.5"]
        close_cols = ["AvgC>2.5", "AvgC<2.5"]
        index = 0 if side == "Over" else 1
    opening = [result.get(column) for column in open_cols]
    closing = [result.get(column) for column in close_cols]
    if not valid(opening) or not valid(closing):
        return None
    open_raw = [1 / float(value) for value in opening]
    close_raw = [1 / float(value) for value in closing]
    return {"opening_odds": float(opening[index]), "closing_odds": float(closing[index]),
            "opening_no_vig_prob": open_raw[index] / sum(open_raw),
            "closing_no_vig_prob": close_raw[index] / sum(close_raw)}


all_rows = week1_rows("EPL") + week1_rows("EFL Championship") + week2_rows()
datasets = {name: pd.read_csv(path, low_memory=False) for name, path in LEAGUES.items()}
graded = []
for item in all_rows:
    data = datasets[item["league"]]
    match = data[(data["Season"] == "2026/27") & (data["HomeTeam"] == item["home"])
                 & (data["AwayTeam"] == item["away"])]
    if len(match) != 1:
        raise RuntimeError(f"Expected one {item['league']} row for {item['home']} v {item['away']}; got {len(match)}")
    result = match.iloc[0]
    prices = market_prices(result, item["market"], item["side"])
    if prices is None:
        raise RuntimeError(f"Missing average open/close for {item['home']} v {item['away']} {item['market']}")
    taken = item["reference_price"]
    graded.append({**item, "match_date": result["Date"], **prices,
        "model_edge_open_pp": 100 * (item["model_prob"] - prices["opening_no_vig_prob"]),
        "model_edge_close_pp": 100 * (item["model_prob"] - prices["closing_no_vig_prob"]),
        "market_move_clv_pct": 100 * (prices["opening_odds"] / prices["closing_odds"] - 1),
        "reference_price_clv_pct": 100 * (taken / prices["closing_odds"] - 1),
        "beat_close": taken > prices["closing_odds"] + 1e-12,
        "shortened": prices["closing_odds"] < prices["opening_odds"] - 1e-12})

output = pd.DataFrame(graded).sort_values(["week", "league", "match_date", "home", "market"])
path = ROOT / "outputs/results/epl_efl_week1_week2_open_close_clv_2026-09-02.csv"
output.to_csv(path, index=False)
for league, slug in (("EPL", "epl"), ("EFL Championship", "efl_championship")):
    output[output["league"] == league].to_csv(
        ROOT / f"outputs/results/{slug}_week1_week2_open_close_clv_2026-09-02.csv", index=False)

def summary(sample: pd.DataFrame) -> dict:
    return {"bets": len(sample), "mean_model_edge_open_pp": sample["model_edge_open_pp"].mean(),
            "mean_model_edge_close_pp": sample["model_edge_close_pp"].mean(),
            "mean_market_move_clv_pct": sample["market_move_clv_pct"].mean(),
            "mean_reference_price_clv_pct": sample["reference_price_clv_pct"].mean(),
            "shortened": int(sample["shortened"].sum()), "beat_close": int(sample["beat_close"].sum())}

print(output[["week", "league", "home", "away", "market", "selection", "reference_price",
              "opening_odds", "closing_odds", "model_edge_open_pp", "model_edge_close_pp",
              "market_move_clv_pct", "reference_price_clv_pct", "beat_close"]].to_string(index=False))
for week in (1, 2):
    print("WEEK", week, summary(output[output["week"] == week]))
    for league in LEAGUES:
        print(" ", league, summary(output[(output["week"] == week) & (output["league"] == league)]))
print(path)
