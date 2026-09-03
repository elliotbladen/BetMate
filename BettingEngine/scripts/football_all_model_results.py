"""Evaluate every frozen EPL/EFL Week 1-2 1X2 and O/U 2.5 prediction."""
from __future__ import annotations

import json
import math
from pathlib import Path
from collections import defaultdict

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/results/all model results"
OUT.mkdir(parents=True, exist_ok=True)


def clip(value: float) -> float:
    return min(1 - 1e-12, max(1e-12, float(value)))


def normalise(values: list[float]) -> list[float]:
    raw = [1 / float(value) for value in values]
    total = sum(raw)
    return [value / total for value in raw]


def predictions() -> list[dict]:
    rows = []
    # EPL Week 1: frozen JSON list.
    for game in json.loads((ROOT / "outputs/football/epl/gw1_prices_2026-08-19.json").read_text()):
        rows.append({"league": "EPL", "week": 1, "home": game["home"], "away": game["away"],
                     "p_home": game["p_home"], "p_draw": game["p_draw"], "p_away": game["p_away"],
                     "p_over": game["p_over25"], "p_under": game["p_under25"], "source": "gw1_prices_2026-08-19.json"})
    # EPL Week 2: normal production columns only.
    for game in pd.read_csv(ROOT / "results/epl/round2_2026_27.csv").to_dict("records"):
        rows.append({"league": "EPL", "week": 2, "home": game["home"], "away": game["away"],
                     "p_home": game["normal_p_home"], "p_draw": game["normal_p_draw"], "p_away": game["normal_p_away"],
                     "p_over": game["normal_p_over25"], "p_under": 1-float(game["normal_p_over25"]),
                     "source": "round2_2026_27.csv"})
    # EFL Week 1: the frozen all-side CLV inputs are the complete forecast archive.
    one = pd.read_csv(ROOT / "outputs/football/championship/gw1_clv_backtest_2026-08-26.csv")
    goals = pd.read_csv(ROOT / "outputs/football/championship/gw1_ou25_clv_backtest_2026-08-26.csv")
    by_game = defaultdict(dict)
    for item in one.to_dict("records"):
        by_game[item["game"]][f"p_{str(item['side']).lower()}"] = float(item["model_prob"])
    for item in goals.to_dict("records"):
        by_game[item["game"]][f"p_{str(item['side']).lower()}"] = float(item["model_prob"])
    for name, game in by_game.items():
        home, away = name.split(" v ", 1)
        rows.append({"league": "EFL Championship", "week": 1, "home": home, "away": away,
                     "p_home": game["p_h"], "p_draw": game["p_d"], "p_away": game["p_a"],
                     "p_over": game["p_over"], "p_under": game["p_under"],
                     "source": "gw1_clv_backtest frozen probabilities"})
    # EFL Week 2: normal model only; player shadow is deliberately excluded.
    payload = json.loads((ROOT / "outputs/football/championship/gw2_prices_2026-08-19.json").read_text())
    for game in payload["games"]:
        rows.append({"league": "EFL Championship", "week": 2, "home": game["home"], "away": game["away"],
                     "p_home": game["p_home"], "p_draw": game["p_draw"], "p_away": game["p_away"],
                     "p_over": game["p_over25"], "p_under": game["p_under25"],
                     "source": "gw2_prices_2026-08-19.json"})
    return rows


DATA = {
    "EPL": pd.read_csv(ROOT / "ml/football/data/epl/matches/epl_matches.csv", low_memory=False),
    "EFL Championship": pd.read_csv(ROOT / "ml/football/data/championship/matches/championship_matches.csv", low_memory=False),
}

one_rows, total_rows, match_rows = [], [], []
for pred in predictions():
    data = DATA[pred["league"]]
    match = data[(data["Season"] == "2026/27") & (data["HomeTeam"] == pred["home"])
                 & (data["AwayTeam"] == pred["away"])]
    if len(match) != 1:
        raise RuntimeError(f"Expected one result for {pred['league']} W{pred['week']} {pred['home']} v {pred['away']}; got {len(match)}")
    result = match.iloc[0]
    opening_1x2 = [float(result[x]) for x in ("AvgH", "AvgD", "AvgA")]
    closing_1x2 = [float(result[x]) for x in ("AvgCH", "AvgCD", "AvgCA")]
    opening_ou = [float(result[x]) for x in ("Avg>2.5", "Avg<2.5")]
    closing_ou = [float(result[x]) for x in ("AvgC>2.5", "AvgC<2.5")]
    if not all(math.isfinite(x) and x > 1 for x in opening_1x2 + closing_1x2 + opening_ou + closing_ou):
        raise RuntimeError(f"Incomplete market for {pred['home']} v {pred['away']}")
    open_p = normalise(opening_1x2); close_p = normalise(closing_1x2)
    open_ou_p = normalise(opening_ou); close_ou_p = normalise(closing_ou)
    model = [float(pred["p_home"]), float(pred["p_draw"]), float(pred["p_away"])]
    actual_side = "H" if result["FTR"] == "H" else "D" if result["FTR"] == "D" else "A"
    actual_index = {"H": 0, "D": 1, "A": 2}[actual_side]
    actual_goals = int(result["FTHG"] + result["FTAG"])
    actual_over = actual_goals > 2.5
    model_over = float(pred["p_over"])
    open_over = open_ou_p[0]; close_over = close_ou_p[0]
    rps = lambda p: 0.5 * ((p[0] - int(actual_index == 0))**2 +
                            ((p[0]+p[1]) - int(actual_index <= 1))**2)
    logloss = lambda p: -math.log(clip(p[actual_index]))
    binary_ll = lambda p: -(int(actual_over)*math.log(clip(p)) + (1-int(actual_over))*math.log(clip(1-p)))
    key = {"league": pred["league"], "week": pred["week"], "date": result["Date"],
           "home": pred["home"], "away": pred["away"], "source": pred["source"]}
    match_rows.append({**key, "score": f"{int(result['FTHG'])}-{int(result['FTAG'])}",
        "actual_1x2": actual_side, "actual_goals": actual_goals,
        "model_rps": rps(model), "opening_market_rps": rps(open_p), "closing_market_rps": rps(close_p),
        "model_1x2_log_loss": logloss(model), "opening_1x2_log_loss": logloss(open_p), "closing_1x2_log_loss": logloss(close_p),
        "model_1x2_pick_correct": int(model.index(max(model)) == actual_index),
        "opening_market_pick_correct": int(open_p.index(max(open_p)) == actual_index),
        "closing_market_pick_correct": int(close_p.index(max(close_p)) == actual_index),
        "model_ou_brier": (model_over-int(actual_over))**2, "opening_ou_brier": (open_over-int(actual_over))**2,
        "closing_ou_brier": (close_over-int(actual_over))**2,
        "model_ou_log_loss": binary_ll(model_over), "opening_ou_log_loss": binary_ll(open_over),
        "closing_ou_log_loss": binary_ll(close_over),
        "model_ou_pick_correct": int((model_over >= .5) == actual_over),
        "opening_ou_pick_correct": int((open_over >= .5) == actual_over),
        "closing_ou_pick_correct": int((close_over >= .5) == actual_over)})
    for side, label, i in (("H", pred["home"]+" win", 0), ("D", "Draw", 1), ("A", pred["away"]+" win", 2)):
        one_rows.append({**key, "market": "1X2", "side": side, "selection": label,
            "model_prob": model[i], "opening_odds": opening_1x2[i], "closing_odds": closing_1x2[i],
            "opening_no_vig_prob": open_p[i], "closing_no_vig_prob": close_p[i],
            "edge_open_pp": 100*(model[i]-open_p[i]), "edge_close_pp": 100*(model[i]-close_p[i]),
            "market_move_pct": 100*(opening_1x2[i]/closing_1x2[i]-1),
            "won": int(i == actual_index), "model_top_pick": int(i == model.index(max(model))),
            "strongest_open_edge": int(i == max(range(3), key=lambda j:model[j]-open_p[j])),
            "strongest_close_edge": int(i == max(range(3), key=lambda j:model[j]-close_p[j]))})
    for side, label, i, probability in (("Over", "Over 2.5", 0, model_over), ("Under", "Under 2.5", 1, 1-model_over)):
        total_rows.append({**key, "market": "O/U 2.5", "side": side, "selection": label,
            "model_prob": probability, "opening_odds": opening_ou[i], "closing_odds": closing_ou[i],
            "opening_no_vig_prob": open_ou_p[i], "closing_no_vig_prob": close_ou_p[i],
            "edge_open_pp": 100*(probability-open_ou_p[i]), "edge_close_pp": 100*(probability-close_ou_p[i]),
            "market_move_pct": 100*(opening_ou[i]/closing_ou[i]-1),
            "won": int(actual_over == (i == 0)), "model_top_pick": int((model_over >= .5) == (i == 0)),
            "strongest_open_edge": int(i == (0 if model_over-open_ou_p[0] >= (1-model_over)-open_ou_p[1] else 1)),
            "strongest_close_edge": int(i == (0 if model_over-close_ou_p[0] >= (1-model_over)-close_ou_p[1] else 1))})

one = pd.DataFrame(one_rows); totals = pd.DataFrame(total_rows); matches = pd.DataFrame(match_rows)

summaries = []
for league in ("EPL", "EFL Championship"):
    slug = "epl" if league == "EPL" else "efl_championship"
    for week in (1, 2):
        o = one[(one.league == league) & (one.week == week)]
        t = totals[(totals.league == league) & (totals.week == week)]
        m = matches[(matches.league == league) & (matches.week == week)]
        o.to_csv(OUT / f"{slug}_week{week}_1x2_all_predictions.csv", index=False)
        t.to_csv(OUT / f"{slug}_week{week}_ou25_all_predictions.csv", index=False)
        m.to_csv(OUT / f"{slug}_week{week}_match_scores.csv", index=False)
        value_o = o[o.strongest_close_edge == 1]; value_t = t[t.strongest_close_edge == 1]
        summaries.extend([
            {"league": league, "week": week, "market": "1X2", "matches": len(m),
             "model_score": m.model_rps.mean(), "opening_market_score": m.opening_market_rps.mean(),
             "closing_market_score": m.closing_market_rps.mean(), "score_name": "RPS_lower_is_better",
             "model_log_loss": m.model_1x2_log_loss.mean(), "closing_market_log_loss": m.closing_1x2_log_loss.mean(),
             "model_pick_accuracy": m.model_1x2_pick_correct.mean(), "closing_market_pick_accuracy": m.closing_market_pick_correct.mean(),
             "mean_abs_edge_open_pp": o.edge_open_pp.abs().mean(), "mean_abs_edge_close_pp": o.edge_close_pp.abs().mean(),
             "value_side_mean_move_pct": value_o.market_move_pct.mean(), "value_side_shortened_rate": (value_o.market_move_pct > 0).mean()},
            {"league": league, "week": week, "market": "O/U 2.5", "matches": len(m),
             "model_score": m.model_ou_brier.mean(), "opening_market_score": m.opening_ou_brier.mean(),
             "closing_market_score": m.closing_ou_brier.mean(), "score_name": "Brier_lower_is_better",
             "model_log_loss": m.model_ou_log_loss.mean(), "closing_market_log_loss": m.closing_ou_log_loss.mean(),
             "model_pick_accuracy": m.model_ou_pick_correct.mean(), "closing_market_pick_accuracy": m.closing_ou_pick_correct.mean(),
             "mean_abs_edge_open_pp": t.edge_open_pp.abs().mean(), "mean_abs_edge_close_pp": t.edge_close_pp.abs().mean(),
             "value_side_mean_move_pct": value_t.market_move_pct.mean(), "value_side_shortened_rate": (value_t.market_move_pct > 0).mean()}
        ])

summary = pd.DataFrame(summaries)
summary.to_csv(OUT / "summary_all_model_results.csv", index=False)

# A pre-close, non-leaking ROI/CLV portfolio: one selection per match/market,
# chosen only from the model versus the de-vigged opening market.
portfolio = pd.concat([one[one.strongest_open_edge == 1], totals[totals.strongest_open_edge == 1]], ignore_index=True)
portfolio["opening_profit"] = portfolio.apply(lambda x: x.opening_odds-1 if x.won else -1.0, axis=1)
portfolio["closing_profit"] = portfolio.apply(lambda x: x.closing_odds-1 if x.won else -1.0, axis=1)
portfolio["positive_open_edge"] = portfolio.edge_open_pp > 0
portfolio.to_csv(OUT / "opening_edge_portfolio_all_predictions.csv", index=False)
roi_rows = []
for (league, week, market), sample in portfolio.groupby(["league", "week", "market"]):
    roi_rows.append({"league": league, "week": week, "market": market, "bets": len(sample),
        "wins": int(sample.won.sum()), "mean_clv_pct": sample.market_move_pct.mean(),
        "positive_clv_rate": (sample.market_move_pct > 0).mean(),
        "opening_profit_units": sample.opening_profit.sum(), "opening_roi_pct": 100*sample.opening_profit.mean(),
        "closing_profit_units": sample.closing_profit.sum(), "closing_roi_pct": 100*sample.closing_profit.mean(),
        "mean_open_edge_pp": sample.edge_open_pp.mean(), "mean_close_edge_pp": sample.edge_close_pp.mean()})
roi_summary = pd.DataFrame(roi_rows)
roi_summary.to_csv(OUT / "clv_roi_summary_all_model_results.csv", index=False)
print(summary.to_string(index=False))
print(roi_summary.to_string(index=False))
print(OUT)
