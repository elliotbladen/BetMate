#!/usr/bin/env python3
"""Backtest archived 2026 AFL rules-model H2H prices against closing odds."""

from pathlib import Path
import argparse
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/backtests"
ROUND_START = {
    7: "2026-04-23", 8: "2026-04-30", 9: "2026-05-07", 10: "2026-05-14",
    11: "2026-05-21", 12: "2026-05-28", 13: "2026-06-04", 14: "2026-06-11",
    15: "2026-06-18", 16: "2026-06-25", 17: "2026-07-02", 18: "2026-07-09",
    19: "2026-07-16", 21: "2026-07-30", 22: "2026-08-06",
}

ALIASES = {
    "crows": "adelaide", "adelaidecrows": "adelaide", "lions": "brisbane",
    "brisbanelions": "brisbane", "blues": "carlton", "carltonblues": "carlton",
    "magpies": "collingwood", "collingwoodmagpies": "collingwood", "bombers": "essendon",
    "essendonbombers": "essendon", "dockers": "fremantle", "fremantledockers": "fremantle",
    "cats": "geelong", "geelongcats": "geelong", "suns": "goldcoast", "goldcoastsuns": "goldcoast",
    "giants": "gws", "gws": "gws", "gwsgiants": "gws", "greaterwesternsydneygiants": "gws", "hawks": "hawthorn",
    "hawthornhawks": "hawthorn", "demons": "melbourne", "melbournedemons": "melbourne",
    "kangaroos": "northmelbourne", "northmelbournekangaroos": "northmelbourne",
    "power": "portadelaide", "portadelaidepower": "portadelaide", "tigers": "richmond",
    "richmondtigers": "richmond", "saints": "stkilda", "stkildasaints": "stkilda",
    "swans": "sydney", "sydneyswans": "sydney", "eagles": "westcoast", "westcoasteagles": "westcoast",
    "bulldogs": "westernbulldogs", "westernbulldogs": "westernbulldogs",
}


def key(v):
    raw = re.sub(r"[^a-z]", "", str(v).lower())
    return ALIASES.get(raw, raw)


def market_data():
    p = ROOT / "outputs/afl_weekly_review/historical/latest.xlsx"
    d = pd.read_excel(p, "Data", header=1)
    d["Date"] = pd.to_datetime(d["Date"])
    d = d[d.Date.dt.year.eq(2026)].copy()
    d["hk"], d["ak"] = d["Home Team"].map(key), d["Away Team"].map(key)
    return d


def ml_text_round(rnd, path):
    text = path.read_text()
    match = re.search(rf"AFL R{rnd} 2026 — ML Shadow Mode.*?Rules H%\s+ML H%.*?\n(?P<table>.*?)\n\s*DIVERGENCE SUMMARY", text, re.S)
    rows = []
    for line in match.group("table").splitlines():
        m = re.match(r"\s*([A-Za-z]+) vs ([A-Za-z]+).*?([0-9]+\.[0-9]+)%\s+([0-9]+\.[0-9]+)%\s+[+-]", line)
        if m:
            hp = float(m[4]) / 100
            rows.append({"home_team": m[1], "away_team": m[2], "home_fair": 1 / hp,
                         "away_fair": 1 / (1 - hp), "round": rnd})
    if len(rows) != 9:
        raise RuntimeError(f"Parsed {len(rows)} ML games from R{rnd} text")
    return pd.DataFrame(rows)


def archived_models(model="rules"):
    frames = []
    if model == "ml":
        frames.append(ml_text_round(8, ROOT / "results/afl/r8_afl_2026.txt"))
        d = pd.read_csv(ROOT / "data/pricing/afl/AFL_PRICING_R09_2026-05-12.csv")
        x = d[["home_team", "away_team", "ml_home_prob"]].copy()
        x["home_fair"] = 1 / x.ml_home_prob
        x["away_fair"] = 1 / (1 - x.ml_home_prob)
        x["round"] = 9
        frames.append(x[["home_team", "away_team", "home_fair", "away_fair", "round"]])
        frames.append(ml_text_round(10, ROOT / "outputs/afl_round_prep/r10_2026/afl_r10_pricing_2026.txt"))
    else:
    # R7-R9 early pricing archives.
        for rnd, p in [
            (7, ROOT / "data/pricing/afl/AFL_PRICING_R07_2026-04-28.csv"),
            (8, ROOT / "data/pricing/afl/AFL_PRICING_R08_2026-05-05.csv"),
            (9, ROOT / "data/pricing/afl/AFL_PRICING_R09_2026-05-12.csv"),
        ]:
            d = pd.read_csv(p)
            home_col = "fair_home_odds" if "fair_home_odds" in d else "home_odds"
            away_col = "fair_away_odds" if "fair_away_odds" in d else "away_odds"
            x = d[["home_team", "away_team", home_col, away_col]].copy()
            x.columns = ["home_team", "away_team", "home_fair", "away_fair"]
            x["round"] = rnd
            frames.append(x)

    # R10 retained as a text pricing sheet.
        text = (ROOT / "outputs/afl_round_prep/r10_2026/afl_r10_pricing_2026.txt").read_text()
        match = re.search(r"AFL R10 2026 — PRICING SHEET.*?\n(?P<table>.*?)\n\s*Hdcp =", text, re.S)
        rows = []
        for line in match.group("table").splitlines():
            m = re.match(r"\s*([A-Za-z]+) vs ([A-Za-z]+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+", line)
            if m:
                rows.append({"home_team": m[1], "away_team": m[2], "home_fair": float(m[3]),
                             "away_fair": float(m[4]), "round": 10})
        frames.append(pd.DataFrame(rows))

    # Structured full-tier archives. R20 was not retained; R23 is not yet completed.
    for rnd in [*range(11, 20), 21, 22]:
        d = pd.read_csv(ROOT / f"results/r{rnd}_afl_2026.csv")
        if model == "ml":
            x = d[["home_team", "away_team", "ml_h2h"]].copy()
            x["home_fair"] = 1 / x.ml_h2h
            x["away_fair"] = 1 / (1 - x.ml_h2h)
            x = x[["home_team", "away_team", "home_fair", "away_fair"]]
        else:
            x = d[["home_team", "away_team", "rules_home_odds", "rules_away_odds"]].copy()
            x.columns = ["home_team", "away_team", "home_fair", "away_fair"]
        x["round"] = rnd
        frames.append(x)
    return pd.concat(frames, ignore_index=True)


def main(model="rules"):
    market = market_data()
    models = archived_models(model)
    bets, games = [], []
    for g in models.itertuples(index=False):
        start = pd.Timestamp(ROUND_START[g.round])
        hit = market[(market.Date.between(start, start + pd.Timedelta(days=4))) &
                     (market.hk.eq(key(g.home_team))) & (market.ak.eq(key(g.away_team)))]
        if len(hit) != 1:
            raise RuntimeError(f"R{g.round}: market count {len(hit)} for {g.home_team} v {g.away_team}")
        m = hit.iloc[0]
        hc, ac = float(m["Home Odds Close"]), float(m["Away Odds Close"])
        overround = 1 / hc + 1 / ac
        hs, aas = float(m["Home Score"]), float(m["Away Score"])
        games.append((g.round, m.Date.date().isoformat(), g.home_team, g.away_team))
        for side, fair, close in [("home", g.home_fair, hc), ("away", g.away_fair, ac)]:
            mp = 1 / float(fair)
            cp = (1 / close) / overround
            edge = mp - cp
            if hs == aas:
                result, profit = "D", close / 2 - 1
            else:
                win = hs > aas if side == "home" else aas > hs
                result, profit = ("W", close - 1) if win else ("L", -1)
            bets.append({"round": g.round, "date": m.Date.date().isoformat(),
                         "match": f"{g.home_team} v {g.away_team}",
                         "selection": g.home_team if side == "home" else g.away_team,
                         "side": side, "model_probability": mp, "closing_no_vig_probability": cp,
                         "probability_edge": edge, "closing_odds": close,
                         "expected_value": mp * close - 1, "result": result, "profit": profit})
    d = pd.DataFrame(bets)
    primary = d[d.probability_edge.ge(.07)].copy()
    ev7 = d[d.expected_value.ge(.07)].copy()
    OUT.mkdir(parents=True, exist_ok=True)
    stem = "afl_2026_ml_h2h" if model == "ml" else "afl_2026_h2h"
    d.to_csv(OUT / f"{stem}_all_model_sides_verified_rounds.csv", index=False)
    primary.to_csv(OUT / f"{stem}_probability_edge_7pct_bets.csv", index=False)
    ev7.to_csv(OUT / f"{stem}_ev_7pct_bets.csv", index=False)
    print(f"games={len(games)} rounds={sorted(set(x[0] for x in games))}")
    for name, x in [("PROB_EDGE_7PP", primary), ("EV_7PCT", ev7)]:
        profit = x.profit.sum()
        print(f"{name}: bets={len(x)} W={(x.result=='W').sum()} L={(x.result=='L').sum()} D={(x.result=='D').sum()} "
              f"stake=${len(x):.2f} return=${len(x)+profit:.2f} profit=${profit:.2f} roi={profit/len(x):.4%}")
        print(x[["round", "date", "selection", "model_probability", "closing_no_vig_probability",
                 "probability_edge", "closing_odds", "result", "profit"]].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["rules", "ml"], default="rules")
    main(parser.parse_args().model)
