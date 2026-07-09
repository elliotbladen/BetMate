"""
xG-fed Dixon-Coles model for EPL.

Key differences from a naive implementation:
  1. Fits on xG (not actual goals) — strips finishing variance
  2. Per-team home advantage γ_i (not a single league constant)
  3. Time-weighted MLE: weight = exp(-decay_rate * days_ago)
     decay_rate = 0.001 → half-life ≈ 693 days (~2 seasons)
  4. Bayesian between-season shrinkage: on season boundary,
     parameters pulled 23% toward league average (ω_b = 0.770)

Usage:
    ratings = fit(matches_df, as_of=date)
    lam, mu = expected_goals(home, away, ratings)
    matrix  = build_scoreline_matrix(lam, mu, rho=ratings["rho"])
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── Constants ─────────────────────────────────────────────────────────────────

DECAY_RATE   = 0.001          # exp(-DECAY_RATE * days) half-life ≈ 693 days
RHO          = -0.13          # Dixon-Coles low-score correction
MAX_GOALS    = 9              # scoreline matrix size
MIN_MATCHES  = 50             # minimum weighted matches before fitting

# Between-season shrinkage: pull toward league average at season boundary
BETWEEN_SEASON_OMEGA = 0.770  # 77% of old params survive, 23% toward average

# Clip params to avoid numerical explosions
PARAM_CLIP = (0.2, 3.0)


# ── Low-score correction ──────────────────────────────────────────────────────

def _tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    elif x == 1 and y == 0:
        return 1.0 + mu * rho
    elif x == 0 and y == 1:
        return 1.0 + lam * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


# ── Time weighting ────────────────────────────────────────────────────────────

def _weights(dates: pd.Series, as_of: datetime, decay_rate: float = DECAY_RATE) -> np.ndarray:
    days_ago = (as_of - dates).dt.total_seconds() / 86400
    w = np.exp(-decay_rate * days_ago.clip(lower=0))
    return w.values


# ── MLE fitting ───────────────────────────────────────────────────────────────

def _neg_log_likelihood(
    params: np.ndarray,
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    home_xg: np.ndarray,
    away_xg: np.ndarray,
    weights: np.ndarray,
    n_teams: int,
    rho: float,
    log_base_h: float,
    log_base_a: float,
) -> float:
    """
    Vectorised negative weighted log-likelihood for Dixon-Coles.

    Parameterisation:
      lam = base_home * exp(att_home + hfa_home - def_away)
      mu  = base_away * exp(att_away  - def_home)

    base_home / base_away are league-average xG (fixed, not fit).
    att/def are team deviations from league average (geometric mean = 1 after normalisation).
    hfa is per-team home deviation (geometric mean = 1, i.e. log mean = 0).

    params layout:
      [0 : n]     log attack
      [n : 2n]    log defence
      [2n : 3n]   log home advantage (per team, relative deviation)
    """
    n = n_teams
    log_att = params[:n]
    log_def = params[n:2*n]
    log_hfa = params[2*n:3*n]

    lam = np.exp(log_base_h + log_att[home_idx] - log_def[away_idx] + log_hfa[home_idx])
    mu  = np.exp(log_base_a + log_att[away_idx]  - log_def[home_idx])
    lam = np.clip(lam, 1e-6, 15.0)
    mu  = np.clip(mu,  1e-6, 15.0)

    x = np.round(home_xg).astype(int)
    y = np.round(away_xg).astype(int)

    # Vectorised Poisson log-PMF
    ll_home = -lam + x * np.log(lam) - gammaln(x + 1)
    ll_away = -mu  + y * np.log(mu)  - gammaln(y + 1)

    # Dixon-Coles low-score tau correction
    tau = np.ones(len(lam))
    tau[(x==0)&(y==0)] = np.maximum(1e-10, 1.0 - lam[(x==0)&(y==0)] * mu[(x==0)&(y==0)] * rho)
    tau[(x==1)&(y==0)] = np.maximum(1e-10, 1.0 + mu[(x==1)&(y==0)] * rho)
    tau[(x==0)&(y==1)] = np.maximum(1e-10, 1.0 + lam[(x==0)&(y==1)] * rho)
    tau[(x==1)&(y==1)] = np.maximum(1e-10, 1.0 - rho)

    return -(weights * (np.log(tau) + ll_home + ll_away)).sum()


def fit(
    df: pd.DataFrame,
    as_of: Optional[datetime] = None,
    rho: float = RHO,
    prev_ratings: Optional[dict] = None,
    decay_rate: float = DECAY_RATE,
    min_matches: int = MIN_MATCHES,
) -> dict:
    """
    Fit Dixon-Coles on time-weighted xG data (or goals for goals-fed leagues —
    the caller decides what goes in the home_xg/away_xg columns).

    df must have: Date, home_team, away_team, home_xg, away_xg
    as_of: fit using data up to this date (exclusive)
    prev_ratings: if provided, used as warm-start for optimisation
                  (implements the Bayesian sequential update)

    Returns dict with keys:
      attack, defence, home_adv, rho, teams, as_of
    """
    if as_of is None:
        as_of = df["Date"].max()

    data = df[df["Date"] < as_of].copy()
    if data.empty or len(data) < min_matches:
        return {}

    w = _weights(data["Date"], as_of, decay_rate)

    # Filter to teams with meaningful data weight (> 5% of a match)
    teams = sorted(set(data["home_team"]) | set(data["away_team"]))
    team_index = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    # Convert team names to integer indices for vectorised likelihood
    home_idx = np.array([team_index[t] for t in data["home_team"].values])
    away_idx = np.array([team_index[t] for t in data["away_team"].values])
    home_xg  = data["home_xg"].values.astype(float)
    away_xg  = data["away_xg"].values.astype(float)

    # Base rates: league-average xG (fixed constants, not fit parameters)
    log_base_h = float(np.log(np.average(home_xg, weights=w).clip(0.5, 5.0)))
    log_base_a = float(np.log(np.average(away_xg, weights=w).clip(0.5, 5.0)))

    # Initial params: warm-start from prev_ratings if available
    if prev_ratings and prev_ratings.get("teams"):
        log_att = np.array([
            np.log(np.clip(prev_ratings["attack"].get(t, 1.0), *PARAM_CLIP))
            for t in teams
        ])
        log_def = np.array([
            np.log(np.clip(prev_ratings["defence"].get(t, 1.0), *PARAM_CLIP))
            for t in teams
        ])
        log_hfa = np.array([
            np.log(np.clip(prev_ratings["home_adv"].get(t, 1.0), 0.1, 3.0))
            for t in teams
        ])
    else:
        log_att = np.zeros(n)
        log_def = np.zeros(n)
        log_hfa = np.zeros(n)   # start at 1.0 (no per-team deviation from base)

    x0 = np.concatenate([log_att, log_def, log_hfa])

    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(home_idx, away_idx, home_xg, away_xg, w, n, rho, log_base_h, log_base_a),
        method="L-BFGS-B",
        options={"maxiter": 500, "ftol": 1e-9},
    )

    params = result.x
    att_raw = np.exp(params[:n])
    def_raw = np.exp(params[n:2*n])
    hfa_raw = np.exp(params[2*n:3*n])

    # Normalise: geometric mean of attack and defence = 1.0
    # (hfa captures per-team deviation from base rate — no normalisation needed)
    att_mean = np.exp(np.mean(np.log(np.clip(att_raw, 1e-6, 1e6))))
    def_mean = np.exp(np.mean(np.log(np.clip(def_raw, 1e-6, 1e6))))

    att_norm = np.clip(att_raw / att_mean, *PARAM_CLIP)
    def_norm = np.clip(def_raw / def_mean, *PARAM_CLIP)
    hfa_norm = np.clip(hfa_raw, 0.1, 3.0)

    attack   = {t: float(att_norm[i]) for i, t in enumerate(teams)}
    defence  = {t: float(def_norm[i]) for i, t in enumerate(teams)}
    home_adv = {t: float(hfa_norm[i]) for i, t in enumerate(teams)}

    # Weighted effective games per team (for promoted-team detection)
    home_w = data.groupby("home_team").apply(lambda g: w[g.index.map(
        lambda idx: data.index.get_loc(idx))].sum() if len(g) > 0 else 0.0)
    away_w = data.groupby("away_team").apply(lambda g: w[g.index.map(
        lambda idx: data.index.get_loc(idx))].sum() if len(g) > 0 else 0.0)

    return {
        "attack":       attack,
        "defence":      defence,
        "home_adv":     home_adv,
        "rho":          rho,
        "base_home_xg": float(np.exp(log_base_h)),
        "base_away_xg": float(np.exp(log_base_a)),
        "teams":        teams,
        "as_of":        as_of,
        "n_matches":    len(data),
        "converged":    result.success,
    }


def apply_between_season_shrinkage(ratings: dict, omega_b: float = BETWEEN_SEASON_OMEGA) -> dict:
    """
    At season boundary: pull parameters omega_b% toward league average.
    This prevents carryover of extreme params from one season to the next.
    """
    if not ratings:
        return ratings

    shrunk = dict(ratings)
    shrunk["attack"]   = {t: omega_b * v + (1 - omega_b) * 1.0
                           for t, v in ratings["attack"].items()}
    shrunk["defence"]  = {t: omega_b * v + (1 - omega_b) * 1.0
                           for t, v in ratings["defence"].items()}
    shrunk["home_adv"] = {t: omega_b * v + (1 - omega_b) * 0.25
                           for t, v in ratings["home_adv"].items()}
    return shrunk


def expected_goals(home: str, away: str, ratings: dict) -> tuple[float, float]:
    """
    Compute expected goals (λ, μ) for a match.

    lam = base_home × att_home × hfa_home / def_away
    mu  = base_away × att_away / def_home

    att/def are relative (1.0 = league average).
    hfa is per-team home deviation (1.0 = exactly base_home advantage).
    base_home/base_away set the absolute scale (league-average xG).
    """
    att    = ratings["attack"]
    defd   = ratings["defence"]
    hfa    = ratings["home_adv"]
    base_h = ratings.get("base_home_xg", 1.569)
    base_a = ratings.get("base_away_xg", 1.263)

    a_h = att.get(home,  1.0)
    d_h = defd.get(home, 1.0)
    a_a = att.get(away,  1.0)
    d_a = defd.get(away, 1.0)
    h_h = hfa.get(home,  1.0)

    lam = base_h * a_h * h_h / d_a
    mu  = base_a * a_a        / d_h

    return float(np.clip(lam, 0.1, 10.0)), float(np.clip(mu, 0.1, 10.0))


def build_scoreline_matrix(
    lam: float,
    mu: float,
    rho: float = RHO,
    max_goals: int = MAX_GOALS,
) -> np.ndarray:
    """
    Build a (max_goals+1) × (max_goals+1) scoreline probability matrix.
    Rows = home goals, columns = away goals.
    """
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            tau = _tau(i, j, lam, mu, rho)
            matrix[i, j] = tau * poisson.pmf(i, lam) * poisson.pmf(j, mu)

    # Normalise (should sum to ~1 already, minor float drift)
    total = matrix.sum()
    if total > 0:
        matrix /= total

    return matrix


def derive_markets(matrix: np.ndarray) -> dict:
    """
    Derive H2H, O/U 2.5, Asian Handicap -0.5 from scoreline matrix.
    Returns fair (no-margin) probabilities and decimal odds.
    """
    n = matrix.shape[0]

    p_home = float(np.sum(np.tril(matrix, -1)))  # home goals > away
    p_draw = float(np.trace(matrix))
    p_away = float(np.sum(np.triu(matrix, 1)))

    # O/U 2.5
    p_over = 0.0
    p_under = 0.0
    for i in range(n):
        for j in range(n):
            if i + j > 2:
                p_over += matrix[i, j]
            else:
                p_under += matrix[i, j]

    # Asian Handicap -0.5 (home -0.5 means home must win outright)
    p_ah_home = p_home  # home -0.5 covers only home wins
    p_ah_away = p_draw + p_away

    def to_odds(p: float) -> float:
        return round(1.0 / p, 3) if p > 0 else 999.0

    return {
        "p_home":    round(p_home, 4),
        "p_draw":    round(p_draw, 4),
        "p_away":    round(p_away, 4),
        "p_over25":  round(p_over, 4),
        "p_under25": round(p_under, 4),
        "p_ah_home": round(p_ah_home, 4),
        "p_ah_away": round(p_ah_away, 4),
        "odds_home":    to_odds(p_home),
        "odds_draw":    to_odds(p_draw),
        "odds_away":    to_odds(p_away),
        "odds_over25":  to_odds(p_over),
        "odds_under25": to_odds(p_under),
        "odds_ah_home": to_odds(p_ah_home),
        "odds_ah_away": to_odds(p_ah_away),
    }
