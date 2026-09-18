"""Build leak-free EPL yellow-card features for Step 2 of the model."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
CARD_RESULTS = ROOT / "data" / "epl" / "cards" / "epl_card_results_2022_23_to_2025_26.csv"
MATCHES = ROOT / "data" / "epl" / "matches" / "epl_matches.csv"
OUT = ROOT / "data" / "epl" / "cards" / "epl_cards_features_2022_23_to_2025_26.csv"

REF_K = 25.0
TEAM_K = 15.0
LEAGUE_HALFLIFE = 150.0


def shrunk(mean: float | None, n: int, baseline: float, k: float) -> float:
    if n <= 0 or mean is None or not np.isfinite(mean):
        return baseline
    return baseline + (mean - baseline) * n / (n + k)


def main() -> None:
    cards = pd.read_csv(CARD_RESULTS)
    cards["date_key"] = pd.to_datetime(cards["Date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    stats = pd.read_csv(MATCHES, low_memory=False)
    stats["date_key"] = pd.to_datetime(stats["Date"]).dt.strftime("%Y-%m-%d")
    stats = stats[["Season", "date_key", "HomeTeam", "AwayTeam", "HF", "AF", "HS", "AS", "HST", "AST"]]
    df = cards.merge(
        stats,
        left_on=["Season", "date_key", "HomeTeam", "AwayTeam"],
        right_on=["Season", "date_key", "HomeTeam", "AwayTeam"],
        how="left",
        validate="one_to_one",
    ).sort_values(["date_key", "HomeTeam", "AwayTeam"]).reset_index(drop=True)
    for c in ["HF", "AF", "HS", "AS", "HST", "AST"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # State stores only matches strictly before the current date. This avoids
    # same-day leakage when several fixtures share a date.
    lg_y = []
    lg_f = []
    ref_y = defaultdict(list)
    ref_f = defaultdict(list)
    team_y = defaultdict(list)
    team_drawn = defaultdict(list)
    team_fouls = defaultdict(list)
    team_y_home = defaultdict(list)
    team_y_away = defaultdict(list)
    ref_games = []
    home_team_games = []
    away_team_games = []
    rows = []

    # Seed the first modelling season from earlier EPL matches already present in
    # the archive. These are strictly historical priors, so the first 2022/23
    # fixture never falls back to a mean calculated from future seasons.
    seed = pd.read_csv(MATCHES, low_memory=False)
    seed["date_key"] = pd.to_datetime(seed["Date"]).dt.strftime("%Y-%m-%d")
    seed = seed[pd.to_datetime(seed["date_key"]) < pd.Timestamp("2022-08-01")]
    for _, r in seed.sort_values("date_key").iterrows():
        referee = str(r.Referee); home = str(r.HomeTeam); away = str(r.AwayTeam)
        hy = float(r.HY); ay = float(r.AY)
        lg_y.append(hy + ay)
        if pd.notna(r.HF) and pd.notna(r.AF):
            lg_f.extend([float(r.HF), float(r.AF)])
        ref_y[referee].append(hy + ay)
        if pd.notna(r.HF) and pd.notna(r.AF): ref_f[referee].append(float(r.HF) + float(r.AF))
        team_y[home].append(hy); team_y[away].append(ay)
        team_drawn[home].append(ay); team_drawn[away].append(hy)
        team_y_home[(home,)].append(hy); team_y_away[(away,)].append(ay)
        if pd.notna(r.HF): team_fouls[home].append(float(r.HF))
        if pd.notna(r.AF): team_fouls[away].append(float(r.AF))

    for date_key, day in df.groupby("date_key", sort=True):
        league_y_mean = float(np.mean(lg_y)) if lg_y else float(df["total_yellow_cards"].mean())
        league_f_mean = float(np.mean(lg_f)) if lg_f else float(df[["HF", "AF"]].stack().mean())
        # Recency-weighted baseline from prior dates only. The weights are based
        # on the number of prior matches, not on any current-day outcome.
        if lg_y:
            weights = np.exp(-np.arange(len(lg_y) - 1, -1, -1) * np.log(2) / LEAGUE_HALFLIFE)
            league_y_mean = float(np.average(lg_y, weights=weights))
        if lg_f:
            weights = np.exp(-np.arange(len(lg_f) - 1, -1, -1) * np.log(2) / LEAGUE_HALFLIFE)
            league_f_mean = float(np.average(lg_f, weights=weights))

        for idx, r in day.iterrows():
            referee = str(r.Referee)
            home, away = str(r.HomeTeam), str(r.AwayTeam)
            ref_y_mean = np.mean(ref_y[referee]) if ref_y[referee] else league_y_mean
            ref_f_mean = np.mean(ref_f[referee]) if ref_f[referee] else league_f_mean
            home_y = np.mean(team_y[home]) if team_y[home] else league_y_mean / 2
            away_y = np.mean(team_y[away]) if team_y[away] else league_y_mean / 2
            home_draw = np.mean(team_drawn[home]) if team_drawn[home] else league_y_mean / 2
            away_draw = np.mean(team_drawn[away]) if team_drawn[away] else league_y_mean / 2
            home_f = np.mean(team_fouls[home]) if team_fouls[home] else league_f_mean / 2
            away_f = np.mean(team_fouls[away]) if team_fouls[away] else league_f_mean / 2
            home_y_home = np.mean(team_y_home[(home,)]) if team_y_home[(home,)] else league_y_mean / 2
            away_y_away = np.mean(team_y_away[(away,)]) if team_y_away[(away,)] else league_y_mean / 2
            row = {
                "Season": r.Season, "Date": r.Date, "HomeTeam": home, "AwayTeam": away,
                "Referee": referee, "HY": r.HY, "AY": r.AY, "HR": r.HR, "AR": r.AR,
                "total_yellow_cards": r.total_yellow_cards,
                "total_red_cards": r.total_red_cards,
                "league_yellow_mean_prior": league_y_mean,
                "league_fouls_mean_prior": league_f_mean,
                "ref_yellow_mean_prior": shrunk(ref_y_mean, len(ref_y[referee]), league_y_mean, REF_K),
                "ref_fouls_mean_prior": shrunk(ref_f_mean, len(ref_f[referee]), league_f_mean, REF_K),
                "ref_games_prior": len(ref_y[referee]),
                "home_team_yellow_mean_prior": shrunk(home_y, len(team_y[home]), league_y_mean / 2, TEAM_K),
                "away_team_yellow_mean_prior": shrunk(away_y, len(team_y[away]), league_y_mean / 2, TEAM_K),
                "home_cards_drawn_mean_prior": shrunk(home_draw, len(team_drawn[home]), league_y_mean / 2, TEAM_K),
                "away_cards_drawn_mean_prior": shrunk(away_draw, len(team_drawn[away]), league_y_mean / 2, TEAM_K),
                "home_fouls_mean_prior": shrunk(home_f, len(team_fouls[home]), league_f_mean / 2, TEAM_K),
                "away_fouls_mean_prior": shrunk(away_f, len(team_fouls[away]), league_f_mean / 2, TEAM_K),
                "home_team_games_prior": len(team_y[home]),
                "away_team_games_prior": len(team_y[away]),
                "home_yellow_home_mean_prior": shrunk(home_y_home, len(team_y_home[(home,)]), league_y_mean / 2, TEAM_K),
                "away_yellow_away_mean_prior": shrunk(away_y_away, len(team_y_away[(away,)]), league_y_mean / 2, TEAM_K),
            }
            rows.append(row)

        # Update state only after every fixture on this date has been scored.
        for _, r in day.iterrows():
            referee = str(r.Referee); home = str(r.HomeTeam); away = str(r.AwayTeam)
            total = float(r.total_yellow_cards); fouls_h = float(r.HF) if pd.notna(r.HF) else np.nan
            fouls_a = float(r.AF) if pd.notna(r.AF) else np.nan
            lg_y.append(total)
            if np.isfinite(fouls_h) and np.isfinite(fouls_a): lg_f.extend([fouls_h, fouls_a])
            ref_y[referee].append(total); team_y[home].append(float(r.HY)); team_y[away].append(float(r.AY))
            team_drawn[home].append(float(r.AY)); team_drawn[away].append(float(r.HY))
            team_y_home[(home,)].append(float(r.HY)); team_y_away[(away,)].append(float(r.AY))
            if np.isfinite(fouls_h): team_fouls[home].append(fouls_h)
            if np.isfinite(fouls_a): team_fouls[away].append(fouls_a)
            if np.isfinite(fouls_h) and np.isfinite(fouls_a):
                ref_f[referee].append(fouls_h + fouls_a)

    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"wrote {len(out)} rows to {OUT}")
    print(f"referee cold starts={(out.ref_games_prior == 0).sum()} "
          f"team cold starts={(out.home_team_games_prior == 0).sum() + (out.away_team_games_prior == 0).sum()}")


if __name__ == "__main__":
    main()
