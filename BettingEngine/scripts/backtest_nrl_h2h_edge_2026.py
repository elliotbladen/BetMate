#!/usr/bin/env python3
"""Backtest archived 2026 NRL H2H model prices against closing odds."""

from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "backtests"

ROUND_WINDOWS = {
    9: ("2026-04-23", "2026-04-26"), 10: ("2026-05-01", "2026-05-03"),
    11: ("2026-05-15", "2026-05-17"), 12: ("2026-05-21", "2026-05-24"),
    13: ("2026-05-29", "2026-05-31"), 14: ("2026-06-04", "2026-06-08"),
    15: ("2026-06-11", "2026-06-14"), 16: ("2026-06-19", "2026-06-21"),
    17: ("2026-06-25", "2026-06-28"), 18: ("2026-07-03", "2026-07-05"),
    19: ("2026-07-10", "2026-07-12"), 20: ("2026-07-16", "2026-07-19"),
    21: ("2026-07-23", "2026-07-26"), 22: ("2026-07-30", "2026-08-02"),
    23: ("2026-08-06", "2026-08-09"),
}

ALIASES = {
    "canterburybankstownbulldogs": "bulldogs", "canterburybulldogs": "bulldogs",
    "northqueenslandcowboys": "cowboys", "northqldcowboys": "cowboys",
    "cronullasutherlandsharks": "sharks",
    "cronullasharks": "sharks", "manlywarringahseaeagles": "manly",
    "manlyseaeagles": "manly", "stgeorgeillawarradragons": "dragons",
    "stgeorgedragons": "dragons", "newzealandwarriors": "warriors",
    "southsydneyrabbitohs": "rabbitohs", "sydneyroosters": "roosters",
    "brisbanebroncos": "broncos", "canberraraiders": "raiders",
    "newcastleknights": "knights", "melbournestorm": "storm",
    "parramattaeels": "eels", "penrithpanthers": "panthers",
    "goldcoasttitans": "titans", "weststigers": "tigers",
    "dolphins": "dolphins",
}


def team_key(value):
    raw = re.sub(r"[^a-z]", "", str(value).lower())
    return ALIASES.get(raw, raw)


def load_market():
    p = ROOT / "outputs/nrl_weekly_review/historical/latest.xlsx"
    d = pd.read_excel(p, sheet_name="Data", header=1)
    d["Date"] = pd.to_datetime(d["Date"])
    d = d[d["Date"].dt.year.eq(2026)].copy()
    d["home_key"] = d["Home Team"].map(team_key)
    d["away_key"] = d["Away Team"].map(team_key)
    return d


def load_models():
    frames = []
    # R21 and R23 files in results/ are stale copies of the prior round, not archives
    # of those rounds, so they are deliberately excluded.
    for rnd in [*range(9, 21), 22]:
        p = ROOT / (f"results/nrl/r{rnd}_pricing_2026.csv" if rnd in (9, 10) else f"results/r{rnd}_pricing_2026.csv")
        d = pd.read_csv(p, encoding="cp1252")
        d = d[["home_team", "away_team", "fair_home_odds", "fair_away_odds"]].copy()
        d["round"] = rnd
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def add_round_8(rows, market):
    # Archived R8 report is the only retained source for this round's fair prices.
    r8 = [
        ("North Queensland Cowboys", "Manly-Warringah Sea Eagles", 1.452, 1.60, 6, 38),
        ("Canberra Raiders", "Melbourne Storm", 1.766, 2.10, 26, 22),
        ("Dolphins", "Penrith Panthers", 3.036, 3.45, 22, 23),
        ("New Zealand Warriors", "Gold Coast Titans", 1.118, 1.29, 28, 20),
        ("South Sydney Rabbitohs", "St. George Illawarra Dragons", 3.799, 3.70, 30, 12, "away"),
        ("Wests Tigers", "Brisbane Broncos", 2.205, 2.45, 20, 21, "away"),
        ("Sydney Roosters", "Newcastle Knights", 1.159, 1.20, 38, 24),
        ("Parramatta Eels", "Canterbury-Bankstown Bulldogs", 3.272, 4.20, 38, 20),
    ]
    # The report lists only the selected-side fair price. Derive its opposing probability.
    for item in r8:
        home, away, selected_fair, selected_close, hs, aas, *side = item
        selected_side = side[0] if side else "home"
        selected_prob = 1 / selected_fair
        if selected_side == "home":
            fh, fa = selected_fair, 1 / (1 - selected_prob)
        else:
            fa, fh = selected_fair, 1 / (1 - selected_prob)
        candidates = market[market["Date"].between("2026-04-16", "2026-04-19")]
        hit = candidates[(candidates.home_key.eq(team_key(home))) &
                         (candidates.away_key.eq(team_key(away)))]
        if len(hit) != 1:
            raise RuntimeError(f"Round 8: market match count {len(hit)} for {home} v {away}")
        m = hit.iloc[0]
        rows.append({"round": 8, "date": m["Date"].date().isoformat(), "home_team": home, "away_team": away,
                     "fair_home_odds": fh, "fair_away_odds": fa,
                     "close_home_odds": m["Home Odds Close"], "close_away_odds": m["Away Odds Close"],
                     "home_score": hs, "away_score": aas})


def main():
    market = load_market()
    models = load_models()
    rows = []
    for r in models.itertuples(index=False):
        start, end = map(pd.Timestamp, ROUND_WINDOWS[r.round])
        candidates = market[market["Date"].between(start, end)]
        hit = candidates[(candidates.home_key.eq(team_key(r.home_team))) &
                         (candidates.away_key.eq(team_key(r.away_team)))]
        if len(hit) != 1:
            raise RuntimeError(f"Round {r.round}: market match count {len(hit)} for {r.home_team} v {r.away_team}")
        m = hit.iloc[0]
        rows.append({"round": r.round, "date": m["Date"].date().isoformat(),
                     "home_team": r.home_team, "away_team": r.away_team,
                     "fair_home_odds": r.fair_home_odds, "fair_away_odds": r.fair_away_odds,
                     "close_home_odds": m["Home Odds Close"], "close_away_odds": m["Away Odds Close"],
                     "home_score": m["Home Score"], "away_score": m["Away Score"]})
    add_round_8(rows, market)
    games = pd.DataFrame(rows)

    bets = []
    for g in games.itertuples(index=False):
        sides = ["home", "away"]
        overround = 1 / g.close_home_odds + 1 / g.close_away_odds
        for side in sides:
            fair = g.fair_home_odds if side == "home" else g.fair_away_odds
            close = g.close_home_odds if side == "home" else g.close_away_odds
            model_prob = 1 / fair
            market_prob = (1 / close) / overround
            edge_pp = model_prob - market_prob
            ev = model_prob * close - 1
            won = g.home_score > g.away_score if side == "home" else g.away_score > g.home_score
            bets.append({"round": g.round, "date": g.date, "match": f"{g.home_team} v {g.away_team}",
                         "selection": g.home_team if side == "home" else g.away_team,
                         "side": side, "model_probability": model_prob,
                         "closing_no_vig_probability": market_prob,
                         "probability_edge": edge_pp,
                         "closing_odds": close, "expected_value": ev, "result": "W" if won else "L",
                         "profit": close - 1 if won else -1})
    all_sides = pd.DataFrame(bets)
    primary = all_sides[all_sides.probability_edge.ge(.07)].copy()
    ev7 = all_sides[all_sides.expected_value.ge(.07)].copy()
    # Include R8 in EV test because that is the exact metric preserved by its archive.
    OUT.mkdir(parents=True, exist_ok=True)
    all_sides.to_csv(OUT / "nrl_2026_h2h_all_model_sides_verified_rounds.csv", index=False)
    primary.to_csv(OUT / "nrl_2026_h2h_probability_edge_7pct_bets.csv", index=False)
    ev7.to_csv(OUT / "nrl_2026_h2h_ev_7pct_bets.csv", index=False)
    for label, d in [("PROBABILITY_EDGE_7PP_VERIFIED_ROUNDS", primary),
                     ("EXPECTED_VALUE_7PCT_VERIFIED_ROUNDS", ev7)]:
        stake = len(d); profit = d.profit.sum()
        print(f"{label}: bets={stake} wins={(d.result == 'W').sum()} losses={(d.result == 'L').sum()} "
              f"staked=${stake:.2f} returned=${stake + profit:.2f} profit=${profit:.2f} roi={profit/stake:.4%}")
        print(d[["round", "date", "selection", "model_probability", "closing_no_vig_probability",
                 "probability_edge", "closing_odds", "expected_value", "result", "profit"]].to_string(index=False))


if __name__ == "__main__":
    main()
