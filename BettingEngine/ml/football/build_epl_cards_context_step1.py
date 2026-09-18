"""Build leak-free context features for the EPL cards model.

All rolling values are calculated from matches strictly before the fixture.
The current match's shots, fouls and xG are only added to state after its
features have been emitted.  PPDA is joined with the latest dated value before
kick-off for the same reason.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "epl"
CARD = DATA / "cards" / "epl_cards_features_2022_23_to_2025_26.csv"
MATCH = DATA / "matches" / "epl_matches.csv"
XG = DATA / "xg" / "understat_xg.csv"
PPDA = DATA / "style" / "ppda_dated.csv"
OUT = DATA / "cards" / "epl_cards_context_features_2022_23_to_2025_26.csv"
REPORT = ROOT / "reports" / "epl_cards_step1_context_audit.md"

TARGET_SEASONS = {"2022/23", "2023/24", "2024/25", "2025/26"}
ROLL = 10


def mean(q: deque[float]) -> float:
    return float(np.mean(q)) if q else np.nan


def main() -> None:
    cards = pd.read_csv(CARD)
    cards["Date"] = pd.to_datetime(cards["Date"], dayfirst=True)
    matches = pd.read_csv(MATCH, parse_dates=["Date"])
    xg = pd.read_csv(XG, parse_dates=["date"])
    ppda = pd.read_csv(PPDA, parse_dates=["date"])

    # Understat is one row per fixture; assert uniqueness before joining.
    xg_key = ["season", "date", "home_team", "away_team"]
    if xg.duplicated(xg_key).any():
        raise ValueError("duplicate Understat fixture keys")
    xg_lookup = xg.set_index(xg_key)[["home_xg", "away_xg"]].to_dict("index")

    # The main match archive supplies historical shots and fouls.  Keep only
    # the outcome fields needed to update the pre-match state.
    match_lookup = matches.set_index(["Season", "Date", "HomeTeam", "AwayTeam"])[
        ["HS", "AS", "HF", "AF"]
    ].to_dict("index")

    ppda_idx: dict[str, tuple[list[pd.Timestamp], list[float]]] = {}
    for team, g in ppda.groupby("team"):
        g = g.dropna(subset=["date", "ppda_rolling10"]).sort_values("date")
        ppda_idx[team] = (g["date"].tolist(), g["ppda_rolling10"].tolist())

    state: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=ROLL)))
    last_date: dict[str, pd.Timestamp] = {}
    rows: list[dict] = []

    # Use the full match archive to seed history, but emit only card-model rows.
    for _, m in matches.sort_values(["Date", "HomeTeam", "AwayTeam"]).iterrows():
        season, date = m["Season"], m["Date"]
        home, away = m["HomeTeam"], m["AwayTeam"]
        hk = (season, date, home, away)
        x = xg_lookup.get(hk)

        def prior(team: str, key: str) -> float:
            return mean(state[team][key])

        def ppda_prior(team: str) -> float:
            if team not in ppda_idx:
                return np.nan
            dates, vals = ppda_idx[team]
            i = bisect_left(dates, date) - 1  # strictly before fixture date
            return float(vals[i]) if i >= 0 else np.nan

        rec = {
            "Season": season, "Date": date, "HomeTeam": home, "AwayTeam": away,
            "home_xg_for_prior": prior(home, "xg_for"),
            "away_xg_for_prior": prior(away, "xg_for"),
            "home_xg_against_prior": prior(home, "xg_against"),
            "away_xg_against_prior": prior(away, "xg_against"),
            "home_shots_prior": prior(home, "shots_for"),
            "away_shots_prior": prior(away, "shots_for"),
            "home_fouls_prior": prior(home, "fouls_for"),
            "away_fouls_prior": prior(away, "fouls_for"),
            "home_ppda_prior": ppda_prior(home),
            "away_ppda_prior": ppda_prior(away),
            "home_prior_matches": len(state[home]["xg_for"]),
            "away_prior_matches": len(state[away]["xg_for"]),
            "home_rest_days": (date - last_date[home]).days if home in last_date else np.nan,
            "away_rest_days": (date - last_date[away]).days if away in last_date else np.nan,
            "xg_source_available": bool(x),
            "match_stats_source_available": hk in match_lookup,
        }
        if season in TARGET_SEASONS:
            rows.append(rec)

        # Update only after emitting the fixture's pre-match values.
        z = match_lookup.get(hk, {})
        if x:
            state[home]["xg_for"].append(float(x["home_xg"]))
            state[home]["xg_against"].append(float(x["away_xg"]))
            state[away]["xg_for"].append(float(x["away_xg"]))
            state[away]["xg_against"].append(float(x["home_xg"]))
        if z:
            state[home]["shots_for"].append(float(z["HS"]))
            state[away]["shots_for"].append(float(z["AS"]))
            state[home]["fouls_for"].append(float(z["HF"]))
            state[away]["fouls_for"].append(float(z["AF"]))
        last_date[home] = date
        last_date[away] = date

    out = cards.merge(pd.DataFrame(rows), on=["Season", "Date", "HomeTeam", "AwayTeam"], how="left", validate="one_to_one")
    out.to_csv(OUT, index=False)

    feature_cols = [c for c in out.columns if c.endswith("_prior") or c.endswith("_days")]
    cov = out.groupby("Season")[feature_cols].apply(lambda d: d.notna().mean()).round(3)
    flags = out.groupby("Season")[["xg_source_available", "match_stats_source_available"]].mean().round(3)
    report = ["# EPL cards Step 1 context audit", "", f"Rows: {len(out)}", "", "All rolling statistics use strictly prior fixtures; current-match statistics are used only after feature emission.", "", "## Coverage by season", "", cov.to_string(), "", "## Source coverage flags", "", flags.to_string()]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n")
    print(f"Saved {len(out)} rows to {OUT}")
    print(cov)


if __name__ == "__main__":
    main()
