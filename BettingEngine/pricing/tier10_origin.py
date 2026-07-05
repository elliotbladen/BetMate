# pricing/tier10_origin.py
# =============================================================================
# Tier 10 — State of Origin overlay
# =============================================================================
#
# Origin squad players are absent from their clubs during Origin camp week.
# The casualty ward scraper never sees them (they're not injured), so T5
# misses them entirely. T10 fills that gap.
#
# Activation: automatic. If the match date falls within a game's
# [camp_start, camp_end) window in data/nrl/origin/{season}.json, T10 fires
# for that game. Otherwise it contributes 0.0 to all adjustments.
#
# Logic is identical to T5 — handicap differential + totals suppression —
# with a wider handicap clamp because a team can lose multiple Origin players.
#
# Data file: Apps/data/nrl/origin/{season}.json
# =============================================================================

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_ORIGIN_PTS = {'elite': 3.0, 'key': 1.5, 'rotation': 0.5}


def _normalise(name: str) -> str:
    """Lowercase, strip hyphens/apostrophes/periods for fuzzy team matching."""
    return re.sub(r"[-'.()]", '', name).lower().strip()


def find_active_origin_game(match_date: str, origin_data: dict) -> Optional[dict]:
    """
    Return the origin game dict whose camp window contains match_date, or None.

    match_date: 'YYYY-MM-DD' string
    origin_data: parsed contents of data/nrl/origin/{season}.json
    """
    if not origin_data:
        return None
    for game in origin_data.get('origin_games', []):
        camp_start = game.get('camp_start', '')
        camp_end   = game.get('camp_end',   '')
        if camp_start and camp_end and camp_start <= match_date < camp_end:
            logger.info(
                'T10: match %s falls in Origin G%d camp window [%s, %s)',
                match_date, game.get('game_number', '?'), camp_start, camp_end,
            )
            return game
    return None


def compute_team_origin_pts(
    team_name: str,
    origin_game: dict,
) -> tuple[float, list[dict]]:
    """
    Sum Origin absence points for players who belong to team_name.

    Returns (total_pts, list_of_matching_player_dicts).
    Matching is fuzzy: hyphens, apostrophes, case ignored.
    """
    norm_team = _normalise(team_name)
    players   = []

    for squad_key in ('nsw_squad', 'qld_squad'):
        for p in origin_game.get(squad_key, []):
            if _normalise(p.get('team', '')) == norm_team:
                pts = _ORIGIN_PTS.get(p.get('tier', 'rotation'), 0.5)
                players.append({**p, '_pts': pts})

    total = sum(p['_pts'] for p in players)
    return round(total, 2), players


def compute_origin_adjustments(
    home_origin_pts: float,
    away_origin_pts: float,
    config: dict,
) -> dict:
    """
    Compute T10 Origin overlay adjustments.

    Identical formula to T5 but with wider default clamp (4.0) since Origin
    can pull multiple players from one team simultaneously.

    Returns dict with: handicap_delta, totals_delta, _debug
    """
    hcap_clamp    = float(config.get('handicap_clamp',   4.0))
    totals_cap    = float(config.get('totals_cap',       -3.0))
    totals_thresh = float(config.get('totals_threshold',  2.5))
    totals_rate   = float(config.get('totals_rate',       -0.3))

    raw_hcap       = away_origin_pts - home_origin_pts
    handicap_delta = max(-hcap_clamp, min(hcap_clamp, raw_hcap))

    combined    = home_origin_pts + away_origin_pts
    excess      = max(0.0, combined - totals_thresh)
    raw_totals  = totals_rate * excess
    totals_delta = max(totals_cap, raw_totals)

    logger.debug(
        'T10 origin: home_pts=%.2f away_pts=%.2f raw_hcap=%.2f hcap_delta=%.2f '
        'combined=%.2f excess=%.2f totals_delta=%.2f',
        home_origin_pts, away_origin_pts, raw_hcap, handicap_delta,
        combined, excess, totals_delta,
    )

    return {
        'handicap_delta': round(handicap_delta, 3),
        'totals_delta':   round(totals_delta,   3),
        '_debug': {
            'home_origin_pts':        home_origin_pts,
            'away_origin_pts':        away_origin_pts,
            'raw_hcap':               round(raw_hcap, 3),
            'combined_pts':           round(combined, 3),
            'excess_above_threshold': round(excess, 3),
            'raw_totals':             round(raw_totals, 3),
        },
    }
