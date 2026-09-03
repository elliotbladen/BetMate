"""UCL adapter for the shared EPL/EFL Dixon-Coles score engine."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from .models import dixon_coles
from .models.elo import build_from_history
from .models.tiers import TeamState, MatchContext, apply_all_tiers, TierParams

ROOT=Path(__file__).resolve().parents[2]; MATCHES=ROOT/"data/ucl/matches/ucl_matches_openfootball.csv"; REPAIRED=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"; XG_MAPPED=ROOT/"data/ucl/xg/ucl_match_xg_mapped.csv"; XG_COMPLETE=ROOT/"data/ucl/matches/ucl_recent_complete_xg_v2.csv"

def load_matches(path=None):
    path = path or (REPAIRED if REPAIRED.exists() else MATCHES)
    raw=pd.read_csv(path); raw["Date"]=pd.to_datetime(raw.kickoff_utc,utc=True); raw["home_team"]=raw.home_club_id; raw["away_team"]=raw.away_club_id
    raw["home_xg"]=raw.home_goals.astype(float); raw["away_xg"]=raw.away_goals.astype(float); raw["xg_source"]="goals_fallback"
    if XG_COMPLETE.exists():
        xg=pd.read_csv(XG_COMPLETE)[["match_id","home_xg","away_xg","xg_source"]].drop_duplicates("match_id")
    elif XG_MAPPED.exists():
        xg=pd.read_csv(XG_MAPPED)[["match_id","home_xg","away_xg","xg_source"]].drop_duplicates("match_id")
    else:
        xg=None
    if xg is not None:
        raw=raw.drop(columns=["home_xg","away_xg","xg_source"]).merge(xg,on="match_id",how="left")
        raw["home_xg"]=raw["home_xg"].fillna(raw["home_goals"].astype(float)); raw["away_xg"]=raw["away_xg"].fillna(raw["away_goals"].astype(float)); raw["xg_source"]=raw["xg_source"].fillna("goals_fallback")
    return raw.sort_values(["Date","match_id"]).reset_index(drop=True)

def fit_before(matches, as_of):
    """Fit shared DC on rows strictly before as_of (no future leakage)."""
    return dixon_coles.fit(matches, as_of=pd.Timestamp(as_of).to_pydatetime(), min_matches=50)

def build_elo_before(matches, as_of):
    """Build the ClubElo component using only matches before the cutoff."""
    h = matches[matches["Date"] < pd.Timestamp(as_of)].copy()
    if len(h) < 10:
        return None
    h["HomeTeam"] = h["home_team"]
    h["AwayTeam"] = h["away_team"]
    h["FTR"] = h.apply(lambda r: "H" if r.home_goals > r.away_goals else ("A" if r.home_goals < r.away_goals else "D"), axis=1)
    h["Season"] = h.get("season", "")
    return build_from_history(h[["Date", "HomeTeam", "AwayTeam", "FTR", "Season"]], as_of=pd.Timestamp(as_of).to_pydatetime())

def _form_rest(matches, team, cutoff):
    h = matches[(matches["Date"] < cutoff) & ((matches.home_team == team) | (matches.away_team == team))].sort_values("Date").tail(5)
    pts = []
    for _, r in h.iterrows():
        is_home = r.home_team == team
        if r.home_goals == r.away_goals: pts.append(1)
        elif (r.home_goals > r.away_goals) == is_home: pts.append(3)
        else: pts.append(0)
    last = matches[(matches["Date"] < cutoff) & ((matches.home_team == team) | (matches.away_team == team))]["Date"]
    rest = int((pd.Timestamp(cutoff) - last.max()).total_seconds() / 86400) if len(last) else None
    return (float(sum(pts)) if pts else None), rest

def _blend_matrix(matrix, target):
    """Reweight scoreline classes to the blended H/D/A probabilities."""
    out = matrix.copy(); masks = [np.tril(np.ones_like(out), -1).astype(bool), np.eye(out.shape[0], dtype=bool), np.triu(np.ones_like(out), 1).astype(bool)]
    for mask, p in zip(masks, target):
        s = out[mask].sum()
        if s > 0: out[mask] *= p / s
    return out / out.sum()

def price(home, away, ratings, elo=None, matches=None, as_of=None, elo_weight=0.30, tier_params=None):
    if not ratings: raise ValueError("insufficient pre-match UCL history")
    lam,mu=dixon_coles.expected_goals(home,away,ratings)
    tier_audit = None
    if matches is not None and as_of is not None:
        fh, rh = _form_rest(matches, home, pd.Timestamp(as_of)); fa, ra = _form_rest(matches, away, pd.Timestamp(as_of))
        ctx = MatchContext(TeamState(home, form5_pts=fh, rest_days=rh), TeamState(away, form5_pts=fa, rest_days=ra))
        adj = apply_all_tiers(lam, mu, ctx, tier_params or TierParams())
        lam, mu, tier_audit = adj.lam_final, adj.mu_final, adj
    matrix=dixon_coles.build_scoreline_matrix(lam,mu,rho=ratings.get("rho",dixon_coles.RHO))
    dc = {"p_home": float(np.tril(matrix, -1).sum()), "p_draw": float(np.trace(matrix)), "p_away": float(np.triu(matrix, 1).sum())}
    blended = dc
    if elo is not None:
        ep = elo.win_probabilities(home, away)
        blended = {k: (1 - elo_weight) * dc[k] + elo_weight * ep[k] for k in ("p_home", "p_draw", "p_away")}
        z = sum(blended.values()); blended = {k: v / z for k, v in blended.items()}
        matrix = _blend_matrix(matrix, [blended["p_home"], blended["p_draw"], blended["p_away"]])
    z = sum(blended.values()); blended = {k: float(v / z) for k, v in blended.items()}
    markets = dixon_coles.derive_markets(matrix)
    markets.update({"p_home": blended["p_home"], "p_draw": blended["p_draw"], "p_away": blended["p_away"]})
    return {"home_team":home,"away_team":away,"lambda_home":lam,"lambda_away":mu,"scoreline_matrix":matrix,"p_home":blended["p_home"],"p_draw":blended["p_draw"],"p_away":blended["p_away"],"p_over25":markets["p_over25"],"p_under25":markets["p_under25"],"p_ah_home":markets["p_ah_home"],"p_ah_away":markets["p_ah_away"],"markets":markets,"dc_probabilities":dc,"engine":"ucl_shared_dixon_coles_elo_tier_stack","elo_weight":elo_weight,"tier_audit":tier_audit}
