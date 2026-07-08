# pricing/tier6_referee.py
# Tier 6 — Referee layer.
#
# Captures officiating tendencies that affect game flow and scoring.
# Primary effect on totals, secondary on handicap, minor on H2H.
# Examples: penalty count tendency, six-again frequency, stop-start profile.
#
# Returns a handicap_delta (margin adjustment) and totals_delta.
#
# Bucket definitions:
#   whistle_heavy  — High penalty/six-again rate; stop-start profile; suppresses scoring
#   flow_heavy     — Low penalty rate; fast play-the-ball; boosts scoring
#   neutral        — Near league average on all measures

import sqlite3
from typing import Optional


def compute_referee_adjustments(
    home_bucket_edge: float,
    away_bucket_edge: float,
    bucket: str,
    config: dict,
    scoring_delta: Optional[float] = None,
    home_bias_adj: Optional[float] = None,
) -> dict:
    """
    Tier 6 referee adjustments.

    handicap_delta:
        If home_bias_adj is provided (real scraped data, season-adjusted):
            Uses home_bias_adj directly — positive favours home team.
            Clamped to ±handicap_clamp (default ±3.5).
        Otherwise falls back to bucket edge difference:
            (home_bucket_edge - away_bucket_edge) * shrink

    totals_delta:
        If scoring_delta is provided (real scraped data from RLP, 2022-2026):
            Uses scoring_delta directly — season-adjusted pts effect of this ref.
            Clamped to ±totals_clamp (default ±4.0).
        Otherwise falls back to bucket lookup:
            whistle_heavy → config value  (default -2.0)
            flow_heavy    → config value  (default +2.0)
            neutral       → 0.0

    Args:
        home_bucket_edge:  avg signed margin for home team under this bucket
        away_bucket_edge:  avg signed margin for away team under this bucket
        bucket:            referee bucket ('whistle_heavy' | 'flow_heavy' | 'neutral')
        config:            tier6_referee config dict from tiers.yaml
        scoring_delta:     real season-adjusted scoring effect (pts) from RLP data,
                           or None if not available (falls back to bucket lookup)
        home_bias_adj:     real season-adjusted home margin effect (pts) from RLP data.
                           Positive = ref favours home team. None → bucket edge fallback.
    """
    SHRINK     = float(config.get('shrink', 1.0))
    hcap_clamp = float(config.get('handicap_clamp', 3.5))
    tot_clamp  = float(config.get('totals_clamp',   4.0))

    if home_bias_adj is not None:
        raw_hcap       = float(home_bias_adj)
        hcap_source    = 'scraped'
    else:
        raw_hcap       = (home_bucket_edge - away_bucket_edge) * SHRINK
        hcap_source    = 'bucket'
    handicap_delta = max(-hcap_clamp, min(hcap_clamp, raw_hcap))

    if scoring_delta is not None:
        # Real data path — use actual measured scoring effect directly
        raw_totals  = float(scoring_delta)
        totals_source = 'scraped'
    else:
        # Fallback to bucket lookup
        base_totals = {
            'whistle_heavy': float(config.get('totals_whistle_heavy', -2.0)),
            'flow_heavy':    float(config.get('totals_flow_heavy',     2.0)),
            'neutral':       float(config.get('totals_neutral',        0.0)),
        }
        raw_totals    = base_totals.get(bucket, 0.0)
        totals_source = 'bucket'

    totals_delta = max(-tot_clamp, min(tot_clamp, raw_totals))

    return {
        'handicap_delta':    round(handicap_delta, 3),
        'totals_delta':      round(totals_delta, 3),
        'bucket':            bucket,
        'scoring_delta':     scoring_delta,
        'home_bias_adj':     home_bias_adj,
        'home_bucket_edge':  home_bucket_edge,
        'away_bucket_edge':  away_bucket_edge,
        '_debug': {
            'raw_hcap':       round(raw_hcap, 3),
            'shrink':         SHRINK,
            'hcap_clamp':     hcap_clamp,
            'hcap_source':    hcap_source,
            'totals_clamp':   tot_clamp,
            'raw_totals':     round(raw_totals, 3),
            'totals_source':  totals_source,
        },
    }


def get_ref_context(
    conn: sqlite3.Connection,
    match_id: int,
    home_team_id: int,
    away_team_id: int,
    season: int,
) -> Optional[dict]:
    """
    Look up the referee assignment, profile, and team bucket stats for a match.

    Queries:
        weekly_ref_assignments → referee_profiles → team_ref_bucket_stats

    Args:
        conn:         active DB connection
        match_id:     canonical match identifier
        home_team_id: home team for bucket edge lookup
        away_team_id: away team for bucket edge lookup
        season:       season for bucket stats lookup

    Returns:
        dict with:
            referee_id       int
            referee_name     str
            bucket           str   ('whistle_heavy' | 'flow_heavy' | 'neutral')
            home_bucket_edge float
            away_bucket_edge float
        or None if no referee assignment exists for this match.
    """
    from db.queries import get_ref_assignment, get_referee_profile, get_team_ref_bucket_edge

    assignment = get_ref_assignment(conn, match_id)
    if assignment is None:
        return None

    referee_id   = assignment['referee_id']
    referee_name = assignment['referee_name']

    profile = get_referee_profile(conn, referee_id)
    if profile is None:
        bucket        = 'neutral'
        scoring_delta = None
        home_bias_adj = None
    else:
        bucket        = profile['bucket']
        scoring_delta = profile.get('scoring_delta')
        home_bias_adj = profile.get('home_bias_adj')

    home_edge = get_team_ref_bucket_edge(conn, home_team_id, bucket, season)
    away_edge = get_team_ref_bucket_edge(conn, away_team_id, bucket, season)

    return {
        'referee_id':        referee_id,
        'referee_name':      referee_name,
        'bucket':            bucket,
        'scoring_delta':     scoring_delta,
        'home_bias_adj':     home_bias_adj,
        'home_bucket_edge':  home_edge,
        'away_bucket_edge':  away_edge,
    }
