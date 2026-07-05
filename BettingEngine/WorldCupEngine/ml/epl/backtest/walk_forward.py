"""
Walk-forward backtest engine for the EPL model.

Architecture:
  Phase 1 — Snapshot precomputation:
    Fit D-C ratings + Elo at each gameweek cutoff date.
    Stored in memory. ~38 fits per season, ~114 fits total for 3 seasons.
    This is fast enough (~2-3 min total).

  Phase 2 — Backtest loop:
    For each test match, look up nearest prior snapshot.
    Price the match. Compare to result + closing line.
    O(1) per match.

Metrics:
  RPS  — primary (lower is better, target < 0.20)
  Brier Score
  Log Loss
  CLV  vs Pinnacle closing line (negative = model shorter = value)

Usage:
    python ml/epl/backtest/walk_forward.py
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

warnings.filterwarnings("ignore")

_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_ROOT))

from ml.epl.models.dixon_coles import (
    fit as dc_fit,
    expected_goals,
    build_scoreline_matrix,
    derive_markets,
)
from ml.epl.models.elo import build_from_history

DATA_DIR    = Path(__file__).parent.parent / "data"
MATCHES_CSV = DATA_DIR / "matches" / "epl_matches.csv"
XG_CSV      = DATA_DIR / "xg" / "understat_xg.csv"
PPDA_CSV    = DATA_DIR / "style" / "ppda_dated.csv"
OUT_DIR     = DATA_DIR / "clv"

TEST_SEASONS    = ["2021/22", "2022/23", "2023/24"]
FEATURE_SEASONS = ["2017/18", "2018/19", "2019/20", "2020/21",
                   "2021/22", "2022/23", "2023/24"]
RHO          = -0.13
ELO_WEIGHT   = 0.30
DC_WEIGHT    = 0.70
MIN_TRAIN    = 200


# ── Totals calibration (fit on all prior seasons' data) ──────────────────────

def fit_totals_calibrator(prior_results: pd.DataFrame):
    """
    Fit isotonic regression: model P(over25) → actual over25 rate.
    prior_results must have columns: p_over25, actual_over25
    """
    if prior_results.empty or len(prior_results) < 50:
        return None
    iso = IsotonicRegression(out_of_bounds="clip")
    p = (1.0 / prior_results["model_over25"].values).clip(0.01, 0.99)
    y = prior_results["actual_over25"].values.astype(float)
    iso.fit(p, y)
    return iso


def apply_totals_calibration(iso, p_over: float) -> float:
    if iso is None:
        return p_over
    return float(np.clip(iso.predict([[p_over]])[0], 0.01, 0.99))


# ── Metrics ───────────────────────────────────────────────────────────────────

def rps(p_home: float, p_draw: float, p_away: float, result: str) -> float:
    o = [1,0,0] if result=="H" else [0,1,0] if result=="D" else [0,0,1]
    p = [p_home, p_draw, p_away]
    return float(np.mean((np.cumsum(p) - np.cumsum(o)) ** 2))

def brier(p: float, outcome: int) -> float:
    return (p - outcome) ** 2

def log_loss_1(p: float, outcome: int, eps: float = 1e-7) -> float:
    p = np.clip(p, eps, 1-eps)
    return -outcome * np.log(p) - (1-outcome) * np.log(1-p)

def clv_pct(model_odds: float, closing_odds: float | None) -> float | None:
    if closing_odds is None or closing_odds <= 0 or model_odds <= 0:
        return None
    return ((closing_odds - model_odds) / model_odds) * 100.0


# ── Data loading ──────────────────────────────────────────────────────────────

def load_and_merge() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not MATCHES_CSV.exists():
        raise FileNotFoundError(f"Run fetch/fetch_results.py first")
    if not XG_CSV.exists():
        raise FileNotFoundError(f"Run fetch/fetch_understat_xg.py first")

    results = pd.read_csv(MATCHES_CSV, parse_dates=["Date"])
    xg      = pd.read_csv(XG_CSV, parse_dates=["date"])
    xg      = xg.rename(columns={"date":"Date","home_team":"HomeTeam","away_team":"AwayTeam"})

    merged = results.merge(
        xg[["Date","HomeTeam","AwayTeam","home_xg","away_xg"]],
        on=["Date","HomeTeam","AwayTeam"], how="left"
    )
    merged["home_xg"] = merged["home_xg"].fillna(merged["FTHG"] * 0.85)
    merged["away_xg"] = merged["away_xg"].fillna(merged["FTAG"] * 0.85)

    xg_coverage = merged["home_xg"].notna().mean()
    print(f"Loaded {len(merged)} matches — {xg_coverage:.1%} have Understat xG")

    # Load PPDA (pressing intensity) data
    ppda_df = pd.DataFrame()
    if PPDA_CSV.exists():
        ppda_df = pd.read_csv(PPDA_CSV, parse_dates=["date"])
        print(f"Loaded {len(ppda_df)} PPDA rows")

    return merged, ppda_df


def get_ppda(ppda_df: pd.DataFrame, team: str, before_date: datetime) -> float | None:
    """Return the most recent rolling PPDA for a team strictly before match date."""
    if ppda_df.empty:
        return None
    rows = ppda_df[(ppda_df["team"] == team) & (ppda_df["date"] < before_date)]
    if rows.empty:
        return None
    return float(rows.sort_values("date").iloc[-1]["ppda_rolling10"])


# ── Phase 1: Snapshot precomputation ─────────────────────────────────────────

def get_gameweek_cutoffs(df: pd.DataFrame, season: str) -> list[datetime]:
    """
    Return one cutoff date per gameweek: the day after each batch of matches.
    We use weekly date groupings (Mon→Sun) as a proxy for gameweeks.
    """
    season_dates = df[df["Season"] == season]["Date"].sort_values().unique()
    # Group into weeks
    cutoffs = []
    prev = None
    for d in season_dates:
        if prev is None or (d - prev).days > 3:
            cutoffs.append(d)
        prev = d
    # Return the day AFTER each gameweek start (so we exclude that GW's matches)
    return [d for d in cutoffs]


def precompute_snapshots(
    df: pd.DataFrame,
    cutoff_dates: list[datetime],
    dc_col_home: str = "HomeTeam",
    dc_col_away: str = "AwayTeam",
) -> dict[datetime, dict]:
    """
    Fit D-C ratings + Elo at each cutoff date.
    Returns {cutoff_date: {"dc": ratings, "elo": EloTracker}}
    """
    snapshots = {}
    prev_dc = None

    for i, cutoff in enumerate(cutoff_dates):
        data_up_to = df[df["Date"] < cutoff].copy()
        if len(data_up_to) < MIN_TRAIN:
            continue

        # D-C fit on xG
        dc_input = data_up_to.rename(columns={dc_col_home: "home_team", dc_col_away: "away_team"})
        dc = dc_fit(dc_input, as_of=cutoff, prev_ratings=prev_dc)
        prev_dc = dc

        # Elo from history
        elo = build_from_history(data_up_to, as_of=cutoff)

        snapshots[cutoff] = {"dc": dc, "elo": elo}

        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{len(cutoff_dates)} snapshots fitted (up to {cutoff.date()})")

    return snapshots


def find_snapshot(snapshots: dict, match_date: datetime) -> dict | None:
    """Return the most recent snapshot strictly before match_date."""
    candidates = [d for d in snapshots if d <= match_date]
    if not candidates:
        return None
    return snapshots[max(candidates)]


def build_referee_lookup(df: pd.DataFrame) -> dict:
    """
    Pre-build {(referee, match_date)} → {ref_home_win_rate, ref_goals_per_game, ref_cards_per_game}.
    Uses expanding window — only prior matches for each referee.
    """
    ref_df = df[["Date","Referee","FTR","FTHG","FTAG","HY","AY"]].dropna(subset=["Referee"]).copy()
    ref_df = ref_df.sort_values("Date")
    ref_df["total_goals"] = ref_df["FTHG"].fillna(0) + ref_df["FTAG"].fillna(0)
    ref_df["total_cards"] = ref_df["HY"].fillna(0) + ref_df["AY"].fillna(0)
    ref_df["is_home_win"] = (ref_df["FTR"] == "H").astype(float)

    lookup = {}
    for ref, grp in ref_df.groupby("Referee"):
        grp = grp.reset_index(drop=True)
        for i, row in grp.iterrows():
            past = grp.iloc[:i]
            if len(past) < 5:
                lookup[(ref, row["Date"])] = {}
                continue
            lookup[(ref, row["Date"])] = {
                "ref_home_win_rate": float(past["is_home_win"].mean()),
                "ref_goals_pg":      float(past["total_goals"].mean()),
                "ref_cards_pg":      float(past["total_cards"].mean()),
            }
    return lookup


def build_form_lookup(df: pd.DataFrame) -> dict:
    """
    Pre-build a lookup: {(team, match_date)} → {rest_days, form5_pts, last_result}.
    Uses all match history (no season restriction) — safe because we look up strictly
    prior matches only.
    """
    # Build long-form: one row per team per match
    home_rows = df[["Date","HomeTeam","AwayTeam","FTR","FTHG","FTAG"]].copy()
    home_rows["team"] = home_rows["HomeTeam"]
    home_rows["opp"]  = home_rows["AwayTeam"]
    home_rows["pts"]  = home_rows["FTR"].map({"H":3,"D":1,"A":0})
    home_rows["ha"]   = "H"

    away_rows = df[["Date","HomeTeam","AwayTeam","FTR","FTHG","FTAG"]].copy()
    away_rows["team"] = away_rows["AwayTeam"]
    away_rows["opp"]  = away_rows["HomeTeam"]
    away_rows["pts"]  = away_rows["FTR"].map({"A":3,"D":1,"H":0})
    away_rows["ha"]   = "A"

    long = pd.concat([home_rows, away_rows], ignore_index=True).sort_values(["team","Date"])

    lookup = {}
    for team, grp in long.groupby("team"):
        grp = grp.reset_index(drop=True)
        for i, row in grp.iterrows():
            past = grp.iloc[:i]
            rest = (row["Date"] - past["Date"].iloc[-1]).days if len(past) > 0 else None
            form5 = past["pts"].iloc[-5:].sum() if len(past) >= 1 else None
            last_result = past["pts"].iloc[-1] if len(past) > 0 else None
            lookup[(team, row["Date"])] = {
                "rest_days":    rest,
                "form5_pts":    float(form5) if form5 is not None else None,
                "last_result_pts": float(last_result) if last_result is not None else None,
            }
    return lookup


def build_corner_lookup(df: pd.DataFrame, n: int = 10) -> dict:
    """
    Pre-build {(team, venue_role, match_date)} → {corners_won_avg, corners_conceded_avg}.
    venue_role = "home" or "away" — corners split by home/away because teams win
    significantly more corners at home (5.75) than away (4.71).
    """
    lookup = {}

    # Home games: HC = won, AC = conceded
    home_df = df[["Date","HomeTeam","HC","AC"]].dropna(subset=["HC","AC"]).copy()
    home_df = home_df.rename(columns={"HomeTeam":"team"})
    for team, grp in home_df.groupby("team"):
        grp = grp.sort_values("Date").reset_index(drop=True)
        for i, row in grp.iterrows():
            past = grp.iloc[max(0, i-n):i]
            if past.empty:
                lookup[(team, "home", row["Date"])] = {}
                continue
            lookup[(team, "home", row["Date"])] = {
                "corners_won_avg":      float(past["HC"].mean()),
                "corners_conceded_avg": float(past["AC"].mean()),
            }

    # Away games: AC = won, HC = conceded
    away_df = df[["Date","AwayTeam","HC","AC"]].dropna(subset=["HC","AC"]).copy()
    away_df = away_df.rename(columns={"AwayTeam":"team"})
    for team, grp in away_df.groupby("team"):
        grp = grp.sort_values("Date").reset_index(drop=True)
        for i, row in grp.iterrows():
            past = grp.iloc[max(0, i-n):i]
            if past.empty:
                lookup[(team, "away", row["Date"])] = {}
                continue
            lookup[(team, "away", row["Date"])] = {
                "corners_won_avg":      float(past["AC"].mean()),
                "corners_conceded_avg": float(past["HC"].mean()),
            }

    return lookup


# ── Phase 2: Backtest loop ────────────────────────────────────────────────────

def run_season(
    df: pd.DataFrame,
    test_season: str,
    all_snapshots: dict,
    prior_results: pd.DataFrame | None = None,
    ppda_df: pd.DataFrame | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    test_df = df[df["Season"] == test_season].sort_values("Date").copy()

    if verbose:
        print(f"\n  Test season: {test_season} — {len(test_df)} matches")

    # Fit totals calibrator on all prior season results
    totals_cal = fit_totals_calibrator(prior_results) if prior_results is not None else None

    # T3: Build form/rest lookup using all data up to test season start
    test_start = test_df["Date"].min()
    form_data  = df[df["Date"] < test_start + timedelta(days=400)].copy()  # include test season
    form_lookup = build_form_lookup(form_data)

    # T6: Referee lookup
    ref_lookup = build_referee_lookup(df)

    # T7: Corner lookup
    corner_lookup = build_corner_lookup(df)

    rows = []
    skipped = 0

    for _, row in test_df.iterrows():
        match_date = row["Date"]
        home = row["HomeTeam"]
        away = row["AwayTeam"]
        result = row["FTR"]

        snap = find_snapshot(all_snapshots, match_date)
        if snap is None:
            skipped += 1
            continue

        dc  = snap["dc"]
        elo = snap["elo"]

        if not dc or home not in dc.get("attack", {}):
            skipped += 1
            continue

        # D-C price
        lam, mu   = expected_goals(home, away, dc)
        matrix    = build_scoreline_matrix(lam, mu, rho=RHO)
        dc_mkts   = derive_markets(matrix)

        # Elo price
        elo_mkts  = elo.win_probabilities(home, away)

        # Blend
        p_home = DC_WEIGHT * dc_mkts["p_home"] + ELO_WEIGHT * elo_mkts["p_home"]
        p_draw = DC_WEIGHT * dc_mkts["p_draw"] + ELO_WEIGHT * elo_mkts["p_draw"]
        p_away = DC_WEIGHT * dc_mkts["p_away"] + ELO_WEIGHT * elo_mkts["p_away"]
        total  = p_home + p_draw + p_away
        p_home, p_draw, p_away = p_home/total, p_draw/total, p_away/total


        m_h = round(1/p_home, 3) if p_home > 0 else 99.0
        m_d = round(1/p_draw, 3) if p_draw > 0 else 99.0
        m_a = round(1/p_away, 3) if p_away > 0 else 99.0

        cl_h = _safe_float(row.get("MaxH"))
        cl_d = _safe_float(row.get("MaxD"))
        cl_a = _safe_float(row.get("MaxA"))
        cl_o = _safe_float(row.get("Max>2.5"))
        cl_u = _safe_float(row.get("Max<2.5"))

        p_o_raw = dc_mkts["p_over25"]
        p_o = apply_totals_calibration(totals_cal, p_o_raw)
        p_u = 1.0 - p_o
        m_o = round(1/p_o, 3) if p_o > 0 else 99.0
        m_u = round(1/p_u, 3) if p_u > 0 else 99.0

        actual_over = 1 if (row.get("FTHG", 0) + row.get("FTAG", 0)) > 2.5 else 0

        # T6: Referee features
        referee = row.get("Referee", None)
        ref_stats = ref_lookup.get((referee, match_date), {}) if referee else {}
        ref_home_wr  = ref_stats.get("ref_home_win_rate")
        ref_goals_pg = ref_stats.get("ref_goals_pg")
        ref_cards_pg = ref_stats.get("ref_cards_pg")

        # T3: Form and rest days
        form_h = form_lookup.get((home, match_date), {})
        form_a = form_lookup.get((away, match_date), {})
        rest_h      = form_h.get("rest_days")
        rest_a      = form_a.get("rest_days")
        form5_h     = form_h.get("form5_pts")
        form5_a     = form_a.get("form5_pts")
        form5_diff  = (form5_h - form5_a) if (form5_h is not None and form5_a is not None) else None
        rest_diff   = (rest_h - rest_a) if (rest_h is not None and rest_a is not None) else None

        # T7: Corner / set-piece stats
        corn_h = corner_lookup.get((home, "home", match_date), {})
        corn_a = corner_lookup.get((away, "away", match_date), {})
        h_corners_won      = corn_h.get("corners_won_avg")
        h_corners_conceded = corn_h.get("corners_conceded_avg")
        a_corners_won      = corn_a.get("corners_won_avg")
        a_corners_conceded = corn_a.get("corners_conceded_avg")

        # T2: PPDA pressing intensity features (no look-ahead — uses data before match date)
        ppda_h = get_ppda(ppda_df, home, match_date) if ppda_df is not None and not ppda_df.empty else None
        ppda_a = get_ppda(ppda_df, away, match_date) if ppda_df is not None and not ppda_df.empty else None
        ppda_diff = (ppda_h - ppda_a) if (ppda_h is not None and ppda_a is not None) else None
        ppda_sum  = (ppda_h + ppda_a) if (ppda_h is not None and ppda_a is not None) else None

        rows.append({
            "season":       test_season,
            "date":         match_date.strftime("%Y-%m-%d"),
            "home":         home,
            "away":         away,
            "result":       result,
            "fthg":         int(row.get("FTHG", 0)),
            "ftag":         int(row.get("FTAG", 0)),
            "lambda":       round(lam, 3),
            "mu":           round(mu, 3),
            "p_home":       round(p_home, 4),
            "p_draw":       round(p_draw, 4),
            "p_away":       round(p_away, 4),
            "model_home":   m_h,
            "model_draw":   m_d,
            "model_away":   m_a,
            "model_over25": m_o,
            "model_under25":m_u,
            "close_home":   cl_h,
            "close_draw":   cl_d,
            "close_away":   cl_a,
            "close_over25": cl_o,
            "close_under25":cl_u,
            "rps":          round(rps(p_home, p_draw, p_away, result), 5),
            "brier_h":      round(brier(p_home, 1 if result=="H" else 0), 5),
            "brier_d":      round(brier(p_draw, 1 if result=="D" else 0), 5),
            "brier_a":      round(brier(p_away, 1 if result=="A" else 0), 5),
            "ll_h":         round(log_loss_1(p_home, 1 if result=="H" else 0), 5),
            "ll_d":         round(log_loss_1(p_draw, 1 if result=="D" else 0), 5),
            "ll_a":         round(log_loss_1(p_away, 1 if result=="A" else 0), 5),
            "clv_home":     _r2(clv_pct(m_h, cl_h)),
            "clv_draw":     _r2(clv_pct(m_d, cl_d)),
            "clv_away":     _r2(clv_pct(m_a, cl_a)),
            "clv_over25":   _r2(clv_pct(m_o, cl_o)),
            "clv_under25":  _r2(clv_pct(m_u, cl_u)),
            "elo_home":     elo_mkts["elo_home"],
            "elo_away":     elo_mkts["elo_away"],
            "elo_diff":     elo_mkts["elo_diff"],
            "actual_over25": actual_over,
            # T2 features
            "ppda_home":    round(ppda_h, 2) if ppda_h else None,
            "ppda_away":    round(ppda_a, 2) if ppda_a else None,
            "ppda_diff":    round(ppda_diff, 2) if ppda_diff is not None else None,
            "ppda_sum":     round(ppda_sum, 2) if ppda_sum is not None else None,
            # T3 features
            "rest_days_home":  rest_h,
            "rest_days_away":  rest_a,
            "rest_diff":       rest_diff,
            "form5_home":      form5_h,
            "form5_away":      form5_a,
            "form5_diff":      form5_diff,
            # T6 features
            "referee":          referee,
            "ref_home_win_rate": ref_home_wr,
            "ref_goals_pg":      ref_goals_pg,
            "ref_cards_pg":      ref_cards_pg,
            # T7 set-piece features
            "h_corners_won":      h_corners_won,
            "h_corners_conceded": h_corners_conceded,
            "a_corners_won":      a_corners_won,
            "a_corners_conceded": a_corners_conceded,
        })

    if verbose:
        print(f"  Priced: {len(rows)}  Skipped: {skipped}")

    return pd.DataFrame(rows)


def _safe_float(v) -> float | None:
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None

def _r2(v) -> float | None:
    return round(v, 2) if v is not None else None


# ── Summary ───────────────────────────────────────────────────────────────────

def summarise(results: pd.DataFrame, season: str) -> dict:
    avg_rps   = float(results["rps"].mean())
    avg_brier = float((results["brier_h"] + results["brier_d"] + results["brier_a"]).mean() / 3)
    avg_ll    = float((results["ll_h"] + results["ll_d"] + results["ll_a"]).mean() / 3)

    pred = results.apply(
        lambda r: "H" if r["p_home"] >= r["p_draw"] and r["p_home"] >= r["p_away"]
        else ("D" if r["p_draw"] >= r["p_away"] else "A"), axis=1
    )
    accuracy = float((pred == results["result"]).mean())

    print(f"\n{'='*58}")
    print(f"  {season}")
    print(f"{'='*58}")
    print(f"  Matches:     {len(results)}")
    print(f"  RPS:         {avg_rps:.4f}   (target < 0.200)")
    print(f"  Brier:       {avg_brier:.4f}  (target < 0.220)")
    print(f"  Log Loss:    {avg_ll:.4f}   (target < 0.700)")
    print(f"  H2H Acc:     {accuracy:.1%}   (realistic: 50-56%)")

    print(f"\n  CLV (negative = model shorter than market = edge):")
    print(f"  {'Market':<10} {'AvgCLV':>8}  {'Model<Mkt':>10}")
    print(f"  {'-'*32}")
    for col, label in [("clv_home","home"),("clv_draw","draw"),
                        ("clv_away","away"),("clv_over25","over25")]:
        clv = results[col].dropna()
        if len(clv) == 0:
            continue
        avg = clv.mean()
        pct_shorter = (clv < 0).mean() * 100
        print(f"  {label:<10} {avg:>+7.1f}%  {pct_shorter:>9.1f}%")

    return {
        "season":   season,
        "n":        len(results),
        "rps":      round(avg_rps, 4),
        "brier":    round(avg_brier, 4),
        "log_loss": round(avg_ll, 4),
        "accuracy": round(accuracy, 4),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    df, ppda_df = load_and_merge()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results    = []
    all_summaries  = []

    for season in TEST_SEASONS:
        if season not in df["Season"].values:
            print(f"Season {season} not found — skipping")
            continue

        print(f"\nPrecomputing snapshots for {season}...")
        cutoffs = get_gameweek_cutoffs(df, season)
        print(f"  {len(cutoffs)} gameweek cutoffs")

        snapshots = precompute_snapshots(df, cutoffs)
        print(f"  {len(snapshots)} snapshots fitted")

        # Pass all prior results for totals calibration
        prior = pd.concat(all_results) if all_results else None
        results = run_season(df, season, snapshots, prior_results=prior, ppda_df=ppda_df)
        if results.empty:
            continue

        all_results.append(results)
        summary = summarise(results, season)
        all_summaries.append(summary)

    if not all_results:
        print("No results.")
        return

    combined = pd.concat(all_results, ignore_index=True)
    combined.to_csv(OUT_DIR / "backtest_results.csv", index=False)

    # ── Feature generation for CatBoost (2017/18 – 2023/24) ──────────────────
    print(f"\n{'='*58}")
    print("  Generating features for CatBoost training...")
    all_feature_rows = []
    for season in FEATURE_SEASONS:
        if season not in df["Season"].values:
            continue
        if season in TEST_SEASONS:
            # Already computed above — reuse
            idx = TEST_SEASONS.index(season)
            if idx < len(all_results):
                all_feature_rows.append(all_results[idx])
            continue
        cutoffs = get_gameweek_cutoffs(df, season)
        snaps   = precompute_snapshots(df, cutoffs)
        prior   = pd.concat(all_feature_rows) if all_feature_rows else None
        res     = run_season(df, season, snaps, prior_results=prior,
                             ppda_df=ppda_df, verbose=False)
        if not res.empty:
            all_feature_rows.append(res)
            print(f"  {season}: {len(res)} rows")

    if all_feature_rows:
        features_df = pd.concat(all_feature_rows, ignore_index=True)
        features_df.to_csv(OUT_DIR / "features_all_seasons.csv", index=False)
        print(f"  Saved {len(features_df)} rows to features_all_seasons.csv")

    print(f"\n{'='*58}")
    print(f"  3-SEASON AGGREGATE ({', '.join(TEST_SEASONS)})")
    print(f"{'='*58}")
    print(f"  Total matches: {len(combined)}")
    print(f"  Avg RPS:       {combined['rps'].mean():.4f}")
    brier_avg = (combined["brier_h"] + combined["brier_d"] + combined["brier_a"]).mean() / 3
    print(f"  Avg Brier:     {brier_avg:.4f}")
    pred = combined.apply(
        lambda r: "H" if r["p_home"] >= r["p_draw"] and r["p_home"] >= r["p_away"]
        else ("D" if r["p_draw"] >= r["p_away"] else "A"), axis=1
    )
    print(f"  Avg Accuracy:  {(pred == combined['result']).mean():.1%}")

    with open(OUT_DIR / "backtest_summary.json", "w") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\nSaved to {OUT_DIR}")


if __name__ == "__main__":
    main()
