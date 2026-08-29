"""
Tier adjustment layer for EPL pricing.

Computes adjustments to base D-C expected goals (λ, μ) based on:
  T2 - PPDA style/pressing matchup
  T3 - Recent form (pts last 5) + rest days (fixture congestion)
  T5 - Injuries (position-based disruption scores)
  T6 - Referee scoring environment

All adjustments are small and bounded — they refine the D-C signal,
they don't override it. D-C is the spine.

Coefficients are research-estimated from EPL analytics literature.
Recalibrate after each full season of live data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ── League baselines (from our 2014/15–2024/25 Understat data) ───────────────
LEAGUE_PPDA_SUM  = 23.0    # avg home_ppda + away_ppda per match
LEAGUE_REF_GOALS = 1.52    # avg home goals (FTHG) per referee game
SHORT_REST_DAYS  = 4       # ≤ this = fatigue applies
FATIGUE_FACTOR   = 0.94    # λ/μ multiplier when team has short rest

# T7 set-piece constants (from our 4,180-match EPL dataset)
LEAGUE_AVG_CORNERS_HOME = 5.75   # avg corners won when playing at home
LEAGUE_AVG_CORNERS_AWAY = 4.71   # avg corners won when playing away
SP_XG_PER_CORNER        = 0.042  # Caley (2014): ~0.042 xG per corner
SP_WEIGHT               = 0.35   # 35% of raw signal — calibration already handles avg bias
SP_CAP                  = 0.08   # hard cap ±0.08 xG per team

# ── T5 injury position weights ────────────────────────────────────────────────
# (attack_weight, defence_weight)
# attack_weight  = fraction of λ lost when this position is absent
# defence_weight = fraction added to opponent's μ (weaker backline = more goals)
# Values from: Caley (2015), Dixon & Coles replication studies, internal calibration
POSITION_WEIGHTS: dict[str, tuple[float, float]] = {
    "GK":  (0.00, 0.06),   # shot-stopping — negligible for attack, significant for defence
    "CB":  (0.01, 0.06),   # aerial, positional — mainly defensive
    "LB":  (0.02, 0.03),   # some attacking threat (crosses) but mostly defensive
    "RB":  (0.02, 0.03),
    "WB":  (0.03, 0.03),   # wing-backs more attacking than FBs
    "DM":  (0.03, 0.05),   # defensive pivot — shields back line
    "CM":  (0.03, 0.04),   # box-to-box
    "AM":  (0.07, 0.02),   # creative hub — major attack loss
    "LW":  (0.06, 0.01),   # wide attacker
    "RW":  (0.06, 0.01),
    "SS":  (0.07, 0.01),   # second striker / shadow striker
    "ST":  (0.09, 0.00),   # main striker — biggest attack impact
    "FW":  (0.08, 0.00),   # forward (generic)
}

# Cap total disruption per team — can't lose more than 25% attack/defence
MAX_DISRUPTION = 0.25

# T2 PPDA coefficient — each 1 unit of ppda_sum above league avg removes this much xG per team
# Research: Carroll (2014) finds PPDA explains ~12% of xG variance
PPDA_GOALS_COEF = -0.007

# T3 form coefficient — each form point advantage adds this much xG
# 15pt max advantage → ±0.12 xG (≈8% on avg λ=1.57)
FORM_GOALS_COEF = 0.008

# T6 referee coefficient — each home-goal above avg ref → this much added to each team's xG
REF_GOALS_COEF = 0.5


# ── League-specific tier parameters ──────────────────────────────────────────
# Defaults are the EPL values above; other leagues supply their own via
# leagues/*.yaml → league_config.LeagueConfig.tier_params.

@dataclass(frozen=True)
class TierParams:
    league_ppda_sum: float = LEAGUE_PPDA_SUM
    league_ref_goals: float = LEAGUE_REF_GOALS
    short_rest_days: int = SHORT_REST_DAYS
    fatigue_factor: float = FATIGUE_FACTOR
    corners_home_avg: float = LEAGUE_AVG_CORNERS_HOME
    corners_away_avg: float = LEAGUE_AVG_CORNERS_AWAY
    sp_xg_per_corner: float = SP_XG_PER_CORNER
    sp_weight: float = SP_WEIGHT
    sp_cap: float = SP_CAP
    ppda_goals_coef: float = PPDA_GOALS_COEF
    form_goals_coef: float = FORM_GOALS_COEF
    ref_goals_coef: float = REF_GOALS_COEF
    # T8: season-reset prior for new Championship teams (set t8_decay_games=0 to disable)
    t8_decay_games: int = 0      # games until prior weight reaches 0 (0 = T8 off)
    t8_max_adj: float = 0.15     # max xG adjustment per team from T8
    t8_elo_scale: float = 600.0  # ELO point difference that equals t8_max_adj
    # T9: new manager bounce
    t9_manager_adj: float = 0.07  # xG boost added to a team with a new manager


DEFAULT_TIER_PARAMS = TierParams()


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class TeamState:
    """What we know about a team before the match."""
    name: str
    ppda: float | None = None           # rolling 10-game pressing intensity
    form5_pts: float | None = None      # points from last 5 matches
    rest_days: int | None = None        # days since last match
    injuries: list[str] = field(default_factory=list)  # list of positions (e.g. ["ST","AM"])
    # T7 set-piece (split by home/away role in this match)
    corners_won_avg: float | None = None       # rolling avg corners won in this venue role
    corners_conceded_avg: float | None = None  # rolling avg corners conceded in this venue role
    # T8 season-reset prior (Championship only)
    t8_elo_diff: float | None = None    # this team's ClubElo minus Championship average (None = not new)
    t8_prior_weight: float = 0.0        # 1.0 = full prior, 0.0 = trust D-C data only
    # T9 manager change
    new_manager: bool = False           # True if team has a new manager this match


@dataclass
class MatchContext:
    """Match-level context."""
    home: TeamState
    away: TeamState
    ref_goals_pg: float | None = None  # referee's avg home goals per game


@dataclass
class AdjustmentBreakdown:
    """Full breakdown of all tier adjustments for transparency."""
    lam_base: float
    mu_base: float
    lam_final: float
    mu_final: float
    t2_ppda_adj: float = 0.0
    t3_form_adj_h: float = 0.0
    t3_form_adj_a: float = 0.0
    t3_rest_adj_h: float = 1.0    # multiplier
    t3_rest_adj_a: float = 1.0
    t5_att_disruption_h: float = 0.0
    t5_def_disruption_h: float = 0.0
    t5_att_disruption_a: float = 0.0
    t5_def_disruption_a: float = 0.0
    t6_ref_adj: float = 0.0
    t7_sp_adj_lam: float = 0.0
    t7_sp_adj_mu: float = 0.0
    t8_adj_lam: float = 0.0
    t8_adj_mu: float = 0.0
    t9_adj_lam: float = 0.0
    t9_adj_mu: float = 0.0


# ── T2: PPDA pressing matchup ─────────────────────────────────────────────────

def t2_ppda_adjustment(ppda_home: float | None, ppda_away: float | None,
                       p: TierParams = DEFAULT_TIER_PARAMS) -> float:
    """
    Returns a symmetric xG adjustment (same for λ and μ).
    High ppda_sum = both teams pressing less = slightly fewer expected goals.
    Low ppda_sum = both teams pressing hard = more transitions, slightly higher xG.

    Returns delta to add to EACH team's xG (can be negative).
    Cap: ±0.15 xG.
    """
    if ppda_home is None or ppda_away is None:
        return 0.0
    ppda_sum = ppda_home + ppda_away
    adj = (ppda_sum - p.league_ppda_sum) * p.ppda_goals_coef
    return float(np.clip(adj, -0.15, 0.15))


# ── T3: Form ──────────────────────────────────────────────────────────────────

def t3_form_adjustment(form5_home: float | None, form5_away: float | None,
                       p: TierParams = DEFAULT_TIER_PARAMS) -> tuple[float, float]:
    """
    Returns (lam_adj, mu_adj) — asymmetric adjustments.
    Home team better form → higher λ. Away team better form → higher μ.
    Cap: ±0.15 xG per team.
    """
    lam_adj = 0.0
    mu_adj  = 0.0
    if form5_home is not None and form5_away is not None:
        form_diff = form5_home - form5_away
        lam_adj = float(np.clip(form_diff * p.form_goals_coef, -0.15, 0.15))
        mu_adj  = float(np.clip(-form_diff * p.form_goals_coef, -0.15, 0.15))
    elif form5_home is not None:
        form_diff = form5_home - 7.5  # compare vs average form (7.5/15)
        lam_adj = float(np.clip(form_diff * p.form_goals_coef, -0.10, 0.10))
    elif form5_away is not None:
        form_diff = form5_away - 7.5
        mu_adj = float(np.clip(form_diff * p.form_goals_coef, -0.10, 0.10))
    return lam_adj, mu_adj


# ── T3: Rest / fatigue ────────────────────────────────────────────────────────

def t3_rest_multipliers(rest_home: int | None, rest_away: int | None,
                        p: TierParams = DEFAULT_TIER_PARAMS) -> tuple[float, float]:
    """
    Returns (lam_mult, mu_mult).
    Short rest (≤4 days) → 6% reduction in expected output.
    """
    lam_mult = p.fatigue_factor if (rest_home is not None and rest_home <= p.short_rest_days) else 1.0
    mu_mult  = p.fatigue_factor if (rest_away is not None and rest_away <= p.short_rest_days) else 1.0
    return lam_mult, mu_mult


# ── T5: Injuries ──────────────────────────────────────────────────────────────

def t5_disruption_score(positions: list[str]) -> tuple[float, float]:
    """
    Given a list of missing player positions (e.g. ["ST", "AM"]),
    returns (attack_disruption, defence_disruption) — both as fractions.
    Attack disruption: reduces λ (home) or μ (away).
    Defence disruption: increases opponent's scoring rate.
    Capped at MAX_DISRUPTION per axis.
    """
    att = 0.0
    dfd = 0.0
    for pos in positions:
        pos_upper = pos.upper().strip()
        w = POSITION_WEIGHTS.get(pos_upper)
        if w is None:
            # Try partial match
            for key in POSITION_WEIGHTS:
                if key in pos_upper or pos_upper in key:
                    w = POSITION_WEIGHTS[key]
                    break
        if w:
            att += w[0]
            dfd += w[1]
    att = min(att, MAX_DISRUPTION)
    dfd = min(dfd, MAX_DISRUPTION)
    return att, dfd


def t5_apply_injuries(
    lam: float,
    mu: float,
    home_injuries: list[str],
    away_injuries: list[str],
) -> tuple[float, float, dict]:
    """
    Apply injury disruption to λ and μ.

    Home injuries:
      - reduce λ (home attacks less)
      - increase μ (home defends less → away scores more)

    Away injuries:
      - reduce μ (away attacks less)
      - increase λ (away defends less → home scores more)
    """
    h_att, h_def = t5_disruption_score(home_injuries)
    a_att, a_def = t5_disruption_score(away_injuries)

    lam_new = lam * (1 - h_att) * (1 + a_def)
    mu_new  = mu  * (1 - a_att) * (1 + h_def)

    return float(lam_new), float(mu_new), {
        "home_att_disruption": h_att,
        "home_def_disruption": h_def,
        "away_att_disruption": a_att,
        "away_def_disruption": a_def,
    }


# ── T6: Referee ───────────────────────────────────────────────────────────────

def t6_referee_adjustment(ref_goals_pg: float | None,
                          p: TierParams = DEFAULT_TIER_PARAMS) -> float:
    """
    Returns a symmetric xG adjustment (same for λ and μ).
    Referee who typically oversees high-scoring games → slight upward revision.
    Cap: ±0.15 xG per team.
    """
    if ref_goals_pg is None:
        return 0.0
    dev = ref_goals_pg - p.league_ref_goals
    adj = dev * p.ref_goals_coef
    return float(np.clip(adj, -0.15, 0.15))


# ── T7: Set-piece xG ─────────────────────────────────────────────────────────

def t7_setpiece_adjustment(
    home: TeamState,
    away: TeamState,
    p: TierParams = DEFAULT_TIER_PARAMS,
) -> tuple[float, float]:
    """
    Returns (sp_lam_adj, sp_mu_adj) — asymmetric set-piece xG adjustments.

    Home set-piece attack lifts λ:
      home corners won above avg → more sp xG for home attack
    Away set-piece defence vulnerability lifts λ:
      away corners conceded above avg → home gets more sp chances

    Away set-piece attack lifts μ (same logic, reversed).

    Weight = 0.35 — calibration already corrects for average league-wide bias.
    Cap = ±0.08 xG per team.
    """
    # Home team: attacking corners (won when playing at home)
    if home.corners_won_avg is not None:
        sp_att_h = (home.corners_won_avg - p.corners_home_avg) * p.sp_xg_per_corner
    else:
        sp_att_h = 0.0

    # Away team: defensive vulnerability (conceded when playing away)
    if away.corners_conceded_avg is not None:
        sp_def_a = (away.corners_conceded_avg - p.corners_home_avg) * p.sp_xg_per_corner
    else:
        sp_def_a = 0.0

    # Away team: attacking corners (won when playing away)
    if away.corners_won_avg is not None:
        sp_att_a = (away.corners_won_avg - p.corners_away_avg) * p.sp_xg_per_corner
    else:
        sp_att_a = 0.0

    # Home team: defensive vulnerability (conceded when playing at home)
    if home.corners_conceded_avg is not None:
        sp_def_h = (home.corners_conceded_avg - p.corners_away_avg) * p.sp_xg_per_corner
    else:
        sp_def_h = 0.0

    sp_lam = float(np.clip((sp_att_h + sp_def_a) * p.sp_weight, -p.sp_cap, p.sp_cap))
    sp_mu  = float(np.clip((sp_att_a + sp_def_h) * p.sp_weight, -p.sp_cap, p.sp_cap))

    return sp_lam, sp_mu


# ── T8: Season-reset prior (Championship) ────────────────────────────────────

def t8_season_prior(
    home: TeamState,
    away: TeamState,
    p: TierParams = DEFAULT_TIER_PARAMS,
) -> tuple[float, float]:
    """
    Season-reset prior for newly promoted/relegated Championship teams.

    When a team has no (or stale) Championship data, D-C falls back to league-average
    attack/defence. T8 corrects this using ClubElo as an independent strength signal.

    Returns (lam_adj, mu_adj):
      lam_adj > 0 = home team is stronger than D-C thinks → boost home attack
      mu_adj  > 0 = away team is stronger than D-C thinks → boost away attack

    The prior_weight stored in TeamState decays from 1.0 (GW1) to 0.0 (GW t8_decay_games)
    as real Championship data accumulates and D-C becomes self-sufficient.

    ELO diff of +600 = t8_max_adj (default ±0.15 xG). Typical new-team range ±100–200 pts.
    Disabled when t8_decay_games=0 (EPL) or both teams have prior_weight=0.
    """
    if p.t8_decay_games <= 0:
        return 0.0, 0.0

    lam_adj = 0.0
    mu_adj  = 0.0

    if home.t8_elo_diff is not None and home.t8_prior_weight > 0:
        raw = (home.t8_elo_diff / p.t8_elo_scale) * p.t8_max_adj
        lam_adj = float(np.clip(raw * home.t8_prior_weight, -p.t8_max_adj, p.t8_max_adj))

    if away.t8_elo_diff is not None and away.t8_prior_weight > 0:
        raw = (away.t8_elo_diff / p.t8_elo_scale) * p.t8_max_adj
        mu_adj = float(np.clip(raw * away.t8_prior_weight, -p.t8_max_adj, p.t8_max_adj))

    return lam_adj, mu_adj


def compute_t8_prior_weight(games_played_this_season: int, p: TierParams) -> float:
    """
    Linear decay: 1.0 at game 0, 0.0 at game t8_decay_games.
    Returns 0.0 if T8 is disabled or team has enough data.
    """
    if p.t8_decay_games <= 0:
        return 0.0
    return float(max(0.0, 1.0 - games_played_this_season / p.t8_decay_games))


# ── T9: Manager change bounce ─────────────────────────────────────────────────

def t9_manager_adjustment(
    home: TeamState,
    away: TeamState,
    p: TierParams = DEFAULT_TIER_PARAMS,
) -> tuple[float, float]:
    """
    New-manager bounce effect.
    Research: teams with new managers show a short-term (~5-10%) performance boost
    as players respond to a change in setup and motivation.

    Returns (lam_adj, mu_adj) — boost to the team with the new manager.
    Cap: t9_manager_adj (default 0.07 xG, ~4-5% on avg λ=1.57).
    """
    lam_adj = p.t9_manager_adj if home.new_manager else 0.0
    mu_adj  = p.t9_manager_adj if away.new_manager else 0.0
    return lam_adj, mu_adj


# ── Master: apply all tiers ───────────────────────────────────────────────────

def apply_all_tiers(
    lam_base: float,
    mu_base: float,
    context: MatchContext,
    params: TierParams = DEFAULT_TIER_PARAMS,
) -> AdjustmentBreakdown:
    """
    Apply T2–T9 adjustments to base D-C expected goals.
    Returns an AdjustmentBreakdown with final λ/μ and full audit trail.
    """
    lam = lam_base
    mu  = mu_base

    # T2: PPDA
    t2_adj = t2_ppda_adjustment(context.home.ppda, context.away.ppda, params)
    lam += t2_adj
    mu  += t2_adj

    # T3: Form
    t3_form_h, t3_form_a = t3_form_adjustment(
        context.home.form5_pts, context.away.form5_pts, params
    )
    lam += t3_form_h
    mu  += t3_form_a

    # T3: Rest
    t3_mult_h, t3_mult_a = t3_rest_multipliers(
        context.home.rest_days, context.away.rest_days, params
    )
    lam *= t3_mult_h
    mu  *= t3_mult_a

    # T5: Injuries
    lam, mu, inj_scores = t5_apply_injuries(
        lam, mu, context.home.injuries, context.away.injuries
    )

    # T6: Referee
    t6_adj = t6_referee_adjustment(context.ref_goals_pg, params)
    lam += t6_adj
    mu  += t6_adj

    # T7: Set-piece
    t7_sp_lam, t7_sp_mu = t7_setpiece_adjustment(context.home, context.away, params)
    lam += t7_sp_lam
    mu  += t7_sp_mu

    # T8: Season-reset prior (Championship new teams)
    t8_lam, t8_mu = t8_season_prior(context.home, context.away, params)
    lam += t8_lam
    mu  += t8_mu

    # T9: Manager change bounce
    t9_lam, t9_mu = t9_manager_adjustment(context.home, context.away, params)
    lam += t9_lam
    mu  += t9_mu

    # Hard floor — can't go below 0.5 expected goals
    lam = max(lam, 0.5)
    mu  = max(mu, 0.5)

    return AdjustmentBreakdown(
        lam_base=lam_base,
        mu_base=mu_base,
        lam_final=round(lam, 3),
        mu_final=round(mu, 3),
        t2_ppda_adj=round(t2_adj, 3),
        t3_form_adj_h=round(t3_form_h, 3),
        t3_form_adj_a=round(t3_form_a, 3),
        t3_rest_adj_h=t3_mult_h,
        t3_rest_adj_a=t3_mult_a,
        t5_att_disruption_h=round(inj_scores["home_att_disruption"], 3),
        t5_def_disruption_h=round(inj_scores["home_def_disruption"], 3),
        t5_att_disruption_a=round(inj_scores["away_att_disruption"], 3),
        t5_def_disruption_a=round(inj_scores["away_def_disruption"], 3),
        t6_ref_adj=round(t6_adj, 3),
        t7_sp_adj_lam=round(t7_sp_lam, 3),
        t7_sp_adj_mu=round(t7_sp_mu, 3),
        t8_adj_lam=round(t8_lam, 3),
        t8_adj_mu=round(t8_mu, 3),
        t9_adj_lam=round(t9_lam, 3),
        t9_adj_mu=round(t9_mu, 3),
    )
