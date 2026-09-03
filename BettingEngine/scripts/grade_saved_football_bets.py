"""Grade frozen EPL/EFL saved selections at flat $1 stakes."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
JOBS = {
    "EPL": (
        ROOT / "outputs/football/epl/gw2_bets_2026-08-31.csv",
        ROOT / "ml/football/data/epl/matches/epl_matches.csv",
    ),
    "EFL Championship": (
        ROOT / "outputs/football/championship/gw3_bets_2026-08-31.csv",
        ROOT / "ml/football/data/championship/matches/championship_matches.csv",
    ),
}


def grade(selection: str, market: str, home: str, away: str, home_goals: int, away_goals: int) -> str:
    text = selection.lower()
    if market == "1X2":
        actual = "home" if home_goals > away_goals else "away" if away_goals > home_goals else "draw"
        wanted = ("draw" if "draw" in text else "home" if text.startswith(home.lower())
                  else "away" if text.startswith(away.lower()) else None)
        if wanted is None:
            raise ValueError(f"Cannot map 1X2 selection {selection!r} to {home} v {away}")
        return "WIN" if wanted == actual else "LOSS"
    if market == "O/U 2.5":
        total = home_goals + away_goals
        wanted_over = text.startswith("over")
        return "WIN" if (total > 2.5) == wanted_over else "LOSS"
    raise ValueError(f"Unsupported market {market}")


rows = []
for league, (bets_path, results_path) in JOBS.items():
    bets = pd.read_csv(bets_path)
    results = pd.read_csv(results_path, low_memory=False)
    results["match_date"] = pd.to_datetime(results["Date"]).dt.strftime("%Y-%m-%d")
    for bet in bets.to_dict("records"):
        found = results[
            (results["match_date"] == bet["match_date"])
            & (results["HomeTeam"] == bet["home"])
            & (results["AwayTeam"] == bet["away"])
        ]
        if len(found) != 1:
            raise RuntimeError(f"{league}: expected one result for {bet['home']} v {bet['away']}, got {len(found)}")
        result = found.iloc[0]
        home_goals, away_goals = int(result["FTHG"]), int(result["FTAG"])
        outcome = grade(bet["selection"], bet["market"], bet["home"], bet["away"], home_goals, away_goals)
        price = float(bet["saved_price"])
        profit = price - 1.0 if outcome == "WIN" else -1.0
        rows.append({"league": league, **bet, "score": f"{home_goals}-{away_goals}",
                     "outcome": outcome, "flat_stake": 1.0, "return": price if outcome == "WIN" else 0.0,
                     "profit": profit, "roi_pct": 100.0 * profit})

out = pd.DataFrame(rows)
out_path = ROOT / "outputs/results/epl_efl_saved_20pct_ev_results_2026-09-02.csv"
out.to_csv(out_path, index=False)

def stats(sample: pd.DataFrame) -> dict[str, float | int]:
    stakes = float(sample["flat_stake"].sum())
    profit = float(sample["profit"].sum())
    return {"bets": len(sample), "wins": int((sample["outcome"] == "WIN").sum()),
            "stakes": stakes, "returns": float(sample["return"].sum()),
            "profit": profit, "roi": 100.0 * profit / stakes if stakes else 0.0}

print(out[["league", "home", "away", "market", "selection", "saved_price", "score", "outcome", "profit", "status"]].to_string(index=False))
for league in JOBS:
    print(league, stats(out[out["league"] == league]))
print("Combined", stats(out))
print("Strict saved status", stats(out[out["status"] == "saved_week2_selection"]))
print(out_path)
