"""
Football match pricer — production script, league-parameterised.

Usage:
    python ml/football/price_match.py --home "Arsenal" --away "Chelsea"
    python ml/football/price_match.py --league championship --home "Leeds" --away "Coventry"

    # With market odds for CLV
    python ml/football/price_match.py --home "Man City" --away "Liverpool" \\
        --mkt-home 2.20 --mkt-draw 3.60 --mkt-away 3.20 --mkt-over25 1.85

    # With referee
    python ml/football/price_match.py --home "Arsenal" --away "Chelsea" --ref "M Oliver"

    # With injuries (positions of missing players, comma-separated)
    python ml/football/price_match.py --home "Arsenal" --away "Chelsea" \\
        --injuries-home "ST,AM" --injuries-away "CB,GK"

    # Full example
    python ml/football/price_match.py \\
        --home "Arsenal" --away "Man City" --date 2026-08-15 \\
        --ref "A Taylor" \\
        --injuries-home "ST" --injuries-away "AM,CM" \\
        --mkt-home 2.40 --mkt-draw 3.50 --mkt-away 3.00 --mkt-over25 1.85

Injury positions: GK CB LB RB WB DM CM AM LW RW SS ST FW
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

from ml.football.models.dixon_coles import fit as dc_fit, expected_goals, build_scoreline_matrix, derive_markets
from ml.football.models.elo import build_from_history
from ml.football.models.tiers import (
    TeamState, MatchContext, apply_all_tiers,
    t5_disruption_score,
)
from ml.football.league_config import load_league, LeagueConfig


def load_data(cfg: LeagueConfig):
    matches = pd.read_csv(cfg.matches_csv, parse_dates=["Date"])

    if cfg.goals_fed:
        merged = matches.copy()
        merged["home_xg"] = merged["FTHG"].astype(float)
        merged["away_xg"] = merged["FTAG"].astype(float)
    else:
        xg = pd.read_csv(cfg.xg_csv, parse_dates=["date"])
        xg = xg.rename(columns={"date":"Date","home_team":"HomeTeam","away_team":"AwayTeam"})
        merged = matches.merge(
            xg[["Date","HomeTeam","AwayTeam","home_xg","away_xg"]],
            on=["Date","HomeTeam","AwayTeam"], how="left"
        )
        merged["home_xg"] = merged["home_xg"].fillna(merged["FTHG"] * cfg.xg_fallback_factor)
        merged["away_xg"] = merged["away_xg"].fillna(merged["FTAG"] * cfg.xg_fallback_factor)

    ppda = pd.DataFrame()
    if cfg.ppda_csv is not None and cfg.ppda_csv.exists():
        ppda = pd.read_csv(cfg.ppda_csv, parse_dates=["date"])

    prior = pd.DataFrame()
    if cfg.results_csv.exists():
        prior = pd.read_csv(cfg.results_csv)

    return merged, ppda, prior


def fit_totals_calibrator(prior: pd.DataFrame):
    if prior.empty or len(prior) < 50:
        return None
    iso = IsotonicRegression(out_of_bounds="clip")
    p = (1.0 / prior["model_over25"].values).clip(0.01, 0.99)
    y = prior["actual_over25"].values.astype(float)
    iso.fit(p, y)
    return iso


def get_ppda(ppda_df: pd.DataFrame, team: str, before: datetime) -> float | None:
    if ppda_df.empty:
        return None
    rows = ppda_df[(ppda_df["team"] == team) & (ppda_df["date"] < before)]
    if rows.empty:
        return None
    return float(rows.sort_values("date").iloc[-1]["ppda_rolling10"])


def get_ref_goals_pg(df: pd.DataFrame, referee: str, before: datetime) -> float | None:
    """Referee's avg home goals/game from all prior matches."""
    ref_matches = df[
        (df["Referee"] == referee) &
        (df["Date"] < before) &
        df["FTHG"].notna()
    ]
    if len(ref_matches) < 5:
        return None
    return float(ref_matches["FTHG"].mean())


def get_form5(df: pd.DataFrame, team: str, before: datetime) -> float | None:
    """Points from team's last 5 matches before this date."""
    home_m = df[df["HomeTeam"] == team][["Date","FTR"]].copy()
    away_m = df[df["AwayTeam"] == team][["Date","FTR"]].copy()
    home_m["pts"] = home_m["FTR"].map({"H":3,"D":1,"A":0})
    away_m["pts"] = away_m["FTR"].map({"A":3,"D":1,"H":0})
    all_m = pd.concat([home_m[["Date","pts"]], away_m[["Date","pts"]]])
    past  = all_m[all_m["Date"] < before].sort_values("Date")
    if len(past) < 1:
        return None
    return float(past["pts"].iloc[-5:].sum())


def get_rest_days(df: pd.DataFrame, team: str, before: datetime) -> int | None:
    """Days since team's last match before this date."""
    home_m = df[df["HomeTeam"] == team]["Date"]
    away_m = df[df["AwayTeam"] == team]["Date"]
    all_dates = pd.concat([home_m, away_m]).sort_values()
    past = all_dates[all_dates < before]
    if past.empty:
        return None
    return int((before - past.iloc[-1]).days)


def get_corner_stats(
    df: pd.DataFrame,
    team: str,
    venue_role: str,    # "home" or "away"
    before: datetime,
    n: int = 10,
) -> tuple[float | None, float | None]:
    """
    Rolling avg corners won and conceded for a team in a specific venue role.
    venue_role="home" → uses HC (won) and AC (conceded) from home games.
    venue_role="away" → uses AC (won) and HC (conceded) from away games.
    Returns (corners_won_avg, corners_conceded_avg).
    """
    if venue_role == "home":
        games = df[(df["HomeTeam"] == team) & (df["Date"] < before)].sort_values("Date")
        won_col, conceded_col = "HC", "AC"
    else:
        games = df[(df["AwayTeam"] == team) & (df["Date"] < before)].sort_values("Date")
        won_col, conceded_col = "AC", "HC"

    recent = games.dropna(subset=[won_col, conceded_col]).iloc[-n:]
    if recent.empty:
        return None, None
    return float(recent[won_col].mean()), float(recent[conceded_col].mean())


def to_odds(p: float) -> float:
    return round(1.0 / p, 2) if p > 0.001 else 999.0


def fmt_clv(model_odds: float, market_odds: float) -> str:
    if market_odds <= 0:
        return ""
    pct = (market_odds - model_odds) / model_odds * 100
    if pct < -3:
        return f"{pct:+.1f}%  ← VALUE (model shorter)"
    elif pct > 3:
        return f"{pct:+.1f}%  model longer"
    else:
        return f"{pct:+.1f}%  aligned"


def price_match(
    home: str,
    away: str,
    as_of: datetime | None = None,
    referee: str | None = None,
    injuries_home: list[str] | None = None,
    injuries_away: list[str] | None = None,
    mkt_home: float = 0,
    mkt_draw: float = 0,
    mkt_away: float = 0,
    mkt_over25: float = 0,
    league: str = "epl",
):
    cfg = load_league(league)
    rho       = float(cfg.model["rho"])
    dc_weight = float(cfg.model["dc_weight"])
    elo_weight = float(cfg.model["elo_weight"])

    if as_of is None:
        as_of = datetime.today()
    if injuries_home is None:
        injuries_home = []
    if injuries_away is None:
        injuries_away = []

    print(f"\nLoading data ({cfg.name})...")
    df, ppda_df, prior = load_data(cfg)
    totals_cal = fit_totals_calibrator(prior)

    print(f"Fitting D-C model (as of {as_of.date()})...")
    dc_input = df[df["Date"] < as_of].rename(
        columns={"HomeTeam":"home_team","AwayTeam":"away_team"}
    )
    ratings = dc_fit(dc_input, as_of=as_of, rho=rho,
                     decay_rate=float(cfg.model["decay_rate"]))

    if not ratings or home not in ratings.get("attack", {}):
        known = sorted(ratings.get("teams", []))
        close = [t for t in known if home.lower() in t.lower() or t.lower() in home.lower()]
        suggestion = f"Did you mean: {close}?" if close else f"Known teams: {known[:10]}..."
        print(f"  '{home}' not found. {suggestion}")
        return

    elo = build_from_history(df[df["Date"] < as_of], as_of=as_of, **cfg.elo)

    # ── Base D-C + Elo ────────────────────────────────────────────────────────
    lam_base, mu_base = expected_goals(home, away, ratings)

    # ── Look up contextual data ───────────────────────────────────────────────
    ppda_h       = get_ppda(ppda_df, home, as_of)
    ppda_a       = get_ppda(ppda_df, away, as_of)
    form5_h      = get_form5(df, home, as_of)
    form5_a      = get_form5(df, away, as_of)
    rest_h       = get_rest_days(df, home, as_of)
    rest_a       = get_rest_days(df, away, as_of)
    ref_goals_pg = get_ref_goals_pg(df, referee, as_of) if referee else None

    # T7: corner stats (home team uses home games, away team uses away games)
    h_corners_won, h_corners_conceded = get_corner_stats(df, home, "home", as_of)
    a_corners_won, a_corners_conceded = get_corner_stats(df, away, "away", as_of)

    # ── T2–T7 adjustments ────────────────────────────────────────────────────
    context = MatchContext(
        home=TeamState(
            name=home,
            ppda=ppda_h,
            form5_pts=form5_h,
            rest_days=rest_h,
            injuries=injuries_home,
            corners_won_avg=h_corners_won,
            corners_conceded_avg=h_corners_conceded,
        ),
        away=TeamState(
            name=away,
            ppda=ppda_a,
            form5_pts=form5_a,
            rest_days=rest_a,
            injuries=injuries_away,
            corners_won_avg=a_corners_won,
            corners_conceded_avg=a_corners_conceded,
        ),
        ref_goals_pg=ref_goals_pg,
    )
    adj = apply_all_tiers(lam_base, mu_base, context, cfg.tier_params)
    lam = adj.lam_final
    mu  = adj.mu_final

    # ── Scoreline matrix → market probabilities ───────────────────────────────
    matrix   = build_scoreline_matrix(lam, mu, rho=rho)
    dc_mkts  = derive_markets(matrix)
    elo_mkts = elo.win_probabilities(home, away)

    p_home = dc_weight * dc_mkts["p_home"] + elo_weight * elo_mkts["p_home"]
    p_draw = dc_weight * dc_mkts["p_draw"] + elo_weight * elo_mkts["p_draw"]
    p_away = dc_weight * dc_mkts["p_away"] + elo_weight * elo_mkts["p_away"]
    total  = p_home + p_draw + p_away
    p_home, p_draw, p_away = p_home/total, p_draw/total, p_away/total

    # Over 2.5 — apply isotonic calibration
    p_o_raw = dc_mkts["p_over25"]
    if totals_cal is not None:
        p_o = float(np.clip(totals_cal.predict([[p_o_raw]])[0], 0.01, 0.99))
    else:
        p_o = p_o_raw
    p_u       = 1.0 - p_o
    p_ah_home = dc_mkts["p_ah_home"]
    p_ah_away = dc_mkts["p_ah_away"]

    # ── Print output ──────────────────────────────────────────────────────────
    W = 68
    print(f"\n{'='*W}")
    print(f"  {home.upper()}  vs  {away.upper()}     {as_of.strftime('%a %d %b %Y')}")
    print(f"{'='*W}")

    # Tier context block
    print(f"\n  CONTEXT")
    print(f"  {'─'*40}")
    print(f"  D-C base xG:   {home} λ={lam_base:.2f}   {away} μ={mu_base:.2f}")
    print(f"  Elo diff:      {elo_mkts['elo_diff']:+.0f} (home advantage in Elo pts)")
    if ppda_h and ppda_a:
        press_h = "high press" if ppda_h < 10 else ("medium" if ppda_h < 13 else "low press")
        press_a = "high press" if ppda_a < 10 else ("medium" if ppda_a < 13 else "low press")
        print(f"  Pressing:      {home} {ppda_h:.1f} ({press_h})   {away} {ppda_a:.1f} ({press_a})")
    if form5_h is not None and form5_a is not None:
        print(f"  Form (last 5): {home} {form5_h:.0f}pts   {away} {form5_a:.0f}pts")
    if rest_h is not None and rest_a is not None:
        rest_h_str = f"{rest_h}d {'⚠ short rest' if rest_h <= 4 else ''}"
        rest_a_str = f"{rest_a}d {'⚠ short rest' if rest_a <= 4 else ''}"
        print(f"  Rest days:     {home} {rest_h_str}   {away} {rest_a_str}")
    if referee:
        ref_note = f"(avg {ref_goals_pg:.2f} home goals/game)" if ref_goals_pg else "(new referee)"
        print(f"  Referee:       {referee} {ref_note}")
    if injuries_home:
        print(f"  Injuries home: {', '.join(injuries_home)}")
    if injuries_away:
        print(f"  Injuries away: {', '.join(injuries_away)}")

    # Tier adjustments block
    print(f"\n  TIER ADJUSTMENTS  (base: λ={lam_base:.2f} μ={mu_base:.2f}  →  adjusted: λ={lam:.2f} μ={mu:.2f})")
    print(f"  {'─'*40}")
    any_adj = False
    if adj.t2_ppda_adj != 0:
        any_adj = True
        print(f"  T2 PPDA:       {adj.t2_ppda_adj:+.3f} xG each team  "
              f"({'pressing suppresses goals' if adj.t2_ppda_adj < 0 else 'passive teams, more open'})")
    if adj.t3_form_adj_h != 0 or adj.t3_form_adj_a != 0:
        any_adj = True
        print(f"  T3 Form:       λ {adj.t3_form_adj_h:+.3f}   μ {adj.t3_form_adj_a:+.3f}")
    if adj.t3_rest_adj_h < 1.0:
        any_adj = True
        print(f"  T3 Rest home:  ×{adj.t3_rest_adj_h:.2f} fatigue penalty ({home})")
    if adj.t3_rest_adj_a < 1.0:
        any_adj = True
        print(f"  T3 Rest away:  ×{adj.t3_rest_adj_a:.2f} fatigue penalty ({away})")
    if injuries_home:
        any_adj = True
        print(f"  T5 Inj home:   attack −{adj.t5_att_disruption_h:.0%}   "
              f"defence −{adj.t5_def_disruption_h:.0%}  (→ μ rises)")
    if injuries_away:
        any_adj = True
        print(f"  T5 Inj away:   attack −{adj.t5_att_disruption_a:.0%}   "
              f"defence −{adj.t5_def_disruption_a:.0%}  (→ λ rises)")
    if adj.t6_ref_adj != 0:
        any_adj = True
        print(f"  T6 Referee:    {adj.t6_ref_adj:+.3f} xG each team  "
              f"({'above-avg scorer' if adj.t6_ref_adj > 0 else 'below-avg scorer'})")
    if adj.t7_sp_adj_lam != 0 or adj.t7_sp_adj_mu != 0:
        any_adj = True
        sp_h_desc = f"{h_corners_won:.1f} won/{h_corners_conceded:.1f} conceded" if h_corners_won else "n/a"
        sp_a_desc = f"{a_corners_won:.1f} won/{a_corners_conceded:.1f} conceded" if a_corners_won else "n/a"
        print(f"  T7 Set-piece:  λ {adj.t7_sp_adj_lam:+.3f}   μ {adj.t7_sp_adj_mu:+.3f}  "
              f"(home corners {sp_h_desc} | away {sp_a_desc})")
    if not any_adj:
        print(f"  No significant adjustments (all tiers within noise threshold)")

    # Markets block
    print(f"\n  MARKETS")
    print(f"  {'─'*62}")
    print(f"  {'Market':<14}  {'Fair P':>7}  {'Fair Odds':>10}  {'Market':>8}  CLV")
    print(f"  {'─'*62}")

    markets = [
        ("Home win",   p_home, mkt_home),
        ("Draw",       p_draw, mkt_draw),
        ("Away win",   p_away, mkt_away),
        ("Over 2.5",   p_o,    mkt_over25),
        ("Under 2.5",  p_u,    0),
        ("AH -0.5 H",  p_ah_home, 0),
        ("AH +0.5 A",  p_ah_away, 0),
    ]

    for label, p, mkt in markets:
        odds    = to_odds(p)
        mkt_str = f"{mkt:.2f}" if mkt > 0 else "   —"
        clv_str = fmt_clv(odds, mkt) if mkt > 0 else ""
        print(f"  {label:<14}  {p:>7.3f}  {odds:>10.2f}  {mkt_str:>8}  {clv_str}")

    # Ratings footer
    att = ratings["attack"]
    dfd = ratings["defence"]
    hfa = ratings["home_adv"]
    print(f"\n  D-C ratings:   {home} att={att.get(home,1):.2f} def={dfd.get(home,1):.2f} hfa={hfa.get(home,1):.2f}"
          f"   |   {away} att={att.get(away,1):.2f} def={dfd.get(away,1):.2f}")
    print(f"  Model data:    {ratings['n_matches']} matches fitted  |  "
          f"{len(prior)} calibration rows  |  as of {as_of.date()}")
    print(f"{'='*W}\n")


def main():
    parser = argparse.ArgumentParser(description="Price a football match")
    parser.add_argument("--league",         default="epl",  help="League config key (leagues/*.yaml)")
    parser.add_argument("--home",           required=True,  help="Home team name")
    parser.add_argument("--away",           required=True,  help="Away team name")
    parser.add_argument("--date",           default=None,   help="As-of date YYYY-MM-DD (default: today)")
    parser.add_argument("--ref",            default=None,   help="Referee name (e.g. 'M Oliver')")
    parser.add_argument("--injuries-home",  default="",     help="Missing home players by position (e.g. 'ST,AM')")
    parser.add_argument("--injuries-away",  default="",     help="Missing away players by position (e.g. 'CB,GK')")
    parser.add_argument("--mkt-home",       type=float, default=0, help="Market home odds")
    parser.add_argument("--mkt-draw",       type=float, default=0, help="Market draw odds")
    parser.add_argument("--mkt-away",       type=float, default=0, help="Market away odds")
    parser.add_argument("--mkt-over25",     type=float, default=0, help="Market over 2.5 odds")
    args = parser.parse_args()

    as_of = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
    inj_h = [p.strip() for p in args.injuries_home.split(",") if p.strip()]
    inj_a = [p.strip() for p in args.injuries_away.split(",") if p.strip()]

    price_match(
        home=args.home,
        away=args.away,
        as_of=as_of,
        referee=args.ref,
        injuries_home=inj_h,
        injuries_away=inj_a,
        mkt_home=args.mkt_home,
        mkt_draw=args.mkt_draw,
        mkt_away=args.mkt_away,
        mkt_over25=args.mkt_over25,
        league=args.league,
    )


if __name__ == "__main__":
    main()
